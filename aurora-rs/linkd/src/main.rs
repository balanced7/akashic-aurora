//! `aurora-linkd`: Aurora's fleet-link daemon.
//!
//! It owns everything that touches untrusted bytes or keys (identity, the ACL log, records, the
//! per-link store, the iroh transport, gossip, blobs, mailbox mode). Python owns everything that
//! touches agents, and talks to it over a local JSON-RPC channel: stdio when `ManagedChild`
//! spawns it, a Unix socket (a named pipe on Windows) for the CLI. It never sees the bus or
//! Redis, and has no shell. See RFC balanced7/akashic-aurora#70 and its Rust addendum.
//!
//! ```text
//! aurora-linkd --home <aurora data root> serve [--stdio] [--offline] [--mailbox] ...
//! aurora-linkd openrpc
//! ```

mod daemon;
mod net;
mod rpc;

use std::path::PathBuf;
use std::sync::{Arc, OnceLock};
use std::time::Duration;

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "aurora-linkd", version, about = "Aurora's fleet-link daemon")]
struct Cli {
    /// The Aurora data root (state/link/ lives under it).
    #[arg(long, env = "AURORA_LINK_HOME", global = true)]
    home: Option<PathBuf>,
    /// Where secrets live (default: <home>/.secrets); keys go in its link/ folder.
    #[arg(long, env = "AKASHIC_SECRETS_DIR", global = true)]
    secrets: Option<PathBuf>,
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Run the daemon.
    Serve {
        /// Serve JSON-RPC on stdin/stdout; exit when stdin closes.
        #[arg(long)]
        stdio: bool,
        /// Do not listen on the RPC socket.
        #[arg(long)]
        no_socket: bool,
        /// No network at all: identity, ACL and bundle work only.
        #[arg(long)]
        offline: bool,
        /// Pull-only mailbox: stores and serves ciphertext, never holds a read key.
        #[arg(long)]
        mailbox: bool,
        /// Relay URL(s) to use instead of n0's (a self-hosted iroh-relay, say).
        #[arg(long = "relay")]
        relays: Vec<String>,
        /// No relays: direct addresses only.
        #[arg(long)]
        no_relay: bool,
        /// Don't publish or resolve addresses through n0's DNS.
        #[arg(long)]
        no_n0: bool,
        /// Don't look for peers on the LAN with mDNS.
        #[arg(long)]
        no_mdns: bool,
        /// Local UDP address to bind (ip:port).
        #[arg(long)]
        bind: Option<std::net::SocketAddr>,
        /// Log every RPC request and response.
        #[arg(long)]
        trace_rpc: bool,
    },
    /// Print the RPC contract as an OpenRPC document.
    Openrpc,
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_env("AURORA_LINKD_LOG")
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("warn,aurora_linkd=info")),
        )
        .init();
    match cli.cmd {
        Cmd::Openrpc => {
            println!("{}", serde_json::to_string_pretty(&rpc::openrpc())?);
            Ok(())
        }
        Cmd::Serve {
            stdio,
            no_socket,
            offline,
            mailbox,
            relays,
            no_relay,
            no_n0,
            no_mdns,
            bind,
            trace_rpc,
        } => {
            let home = cli.home.unwrap_or(std::env::current_dir()?);
            let dirs = daemon::Dirs::new(&home, cli.secrets.as_deref());
            rpc::TRACE.store(trace_rpc, std::sync::atomic::Ordering::Relaxed);
            let opts = net::NetOpts {
                n0: !no_n0,
                mdns: !no_mdns,
                relays,
                no_relay,
                bind,
            };
            tokio::runtime::Builder::new_multi_thread()
                .enable_all()
                .build()?
                .block_on(serve(dirs, stdio, !no_socket, offline, mailbox, opts))
        }
    }
}

async fn serve(
    dirs: daemon::Dirs,
    stdio: bool,
    socket: bool,
    offline: bool,
    mailbox: bool,
    opts: net::NetOpts,
) -> anyhow::Result<()> {
    let d = daemon::Daemon::open(dirs.clone(), mailbox)?;
    let (stop_tx, mut stop_rx) = tokio::sync::watch::channel(false);
    let net_cell: Arc<OnceLock<Arc<net::Net>>> = Arc::new(OnceLock::new());
    let ctx = Arc::new(rpc::Ctx {
        d: d.clone(),
        net_cell: net_cell.clone(),
        offline,
        shutdown: stop_tx.clone(),
    });

    if !offline {
        // The network starts once this install has an identity (it may get one over RPC).
        let d = d.clone();
        let cell = net_cell.clone();
        tokio::spawn(async move {
            loop {
                if d.device().is_ok() {
                    match net::Net::start(d.clone(), opts.clone()).await {
                        Ok(n) => {
                            tracing::info!("listening as {}", aurora_link::codec::hex(n.endpoint.id().as_bytes()));
                            let _ = cell.set(n);
                            return;
                        }
                        Err(e) => tracing::error!("network did not start: {e:#}"),
                    }
                }
                tokio::time::sleep(Duration::from_secs(2)).await;
            }
        });
    }
    if socket {
        let ctx = ctx.clone();
        let path = dirs.socket();
        std::fs::write(dirs.addr_file(), rpc::endpoint_name(&path))?;
        tokio::spawn(async move {
            if let Err(e) = rpc::serve_socket(ctx, path).await {
                tracing::error!("rpc socket: {e:#}");
            }
        });
    }
    if stdio {
        let ctx = ctx.clone();
        let stop = stop_tx.clone();
        tokio::spawn(async move {
            if let Err(e) = rpc::serve_stream(ctx, tokio::io::stdin(), tokio::io::stdout()).await {
                tracing::error!("rpc stdio: {e:#}");
            }
            let _ = stop.send(true); // stdin closed: our parent is gone or done
        });
    }
    if !offline {
        // Housekeeping: receipts every minute, retention and renewal every hour.
        let d = d.clone();
        tokio::spawn(async move {
            let mut ticks: u64 = 0;
            loop {
                tokio::time::sleep(Duration::from_secs(60)).await;
                ticks += 1;
                if let Ok(device) = d.device() {
                    let ids: Vec<String> = d.links.lock().expect("links").keys().cloned().collect();
                    for id in ids {
                        let rec = d.with_link(&id, |l| {
                            let ack = l.ack(&device, vec![], aurora_link::codec::now())?;
                            Ok(match ack {
                                Some(a) => l.store.get(&a)?.map(|s| s.record),
                                None => None,
                            })
                        });
                        if let Ok(Some(r)) = rec {
                            d.push(&id, daemon::Push::Records(vec![r]));
                        }
                    }
                }
                if ticks % 60 == 1
                    && let Err(e) = d.housekeeping()
                {
                    tracing::warn!("housekeeping: {}", e.message);
                }
            }
        });
    }
    if !stdio && !socket {
        anyhow::bail!("nothing to serve: give --stdio or allow the socket");
    }
    let _ = stop_rx.wait_for(|stop| *stop).await;
    if let Some(n) = net_cell.get() {
        n.shutdown().await;
    }
    if socket {
        let _ = std::fs::remove_file(dirs.addr_file());
        #[cfg(unix)]
        let _ = std::fs::remove_file(dirs.socket());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    /// openrpc.json is the checked-in contract Python's types are generated from.
    /// Regenerate with `cargo run -p aurora-linkd -- openrpc > linkd/openrpc.json`.
    #[test]
    fn the_checked_in_openrpc_is_current() {
        let want = serde_json::to_string_pretty(&crate::rpc::openrpc()).unwrap() + "\n";
        let have = std::fs::read_to_string(concat!(env!("CARGO_MANIFEST_DIR"), "/openrpc.json")).unwrap_or_default();
        assert!(have == want, "linkd/openrpc.json is stale: regenerate it");
    }

    #[test]
    fn every_method_is_dispatched() {
        let src = include_str!("rpc.rs");
        for m in crate::rpc::METHODS {
            assert!(src.contains(&format!("\"{}\" =>", m.name)), "{} has no dispatch arm", m.name);
        }
    }
}
