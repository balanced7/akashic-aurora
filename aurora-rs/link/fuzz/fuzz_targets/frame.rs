#![no_main]
//! A sync frame from a connected peer, of every variant, handled by a live session over a real
//! link. p2panda-spaces 0.7.1 crashed on two valid variants; no variant may panic here.
use std::sync::{Mutex, OnceLock};

use aurora_link::engine::Link;
use aurora_link::identity::{Device, new_phrase, root_from_phrase};
use aurora_link::sync::{self, Session};
use libfuzzer_sys::fuzz_target;

fn fixture() -> &'static Mutex<(Link, Device)> {
    static F: OnceLock<Mutex<(Link, Device)>> = OnceLock::new();
    F.get_or_init(|| {
        let root = root_from_phrase(&new_phrase()).unwrap();
        let dev = Device::create(&root, "fuzz", false, aurora_link::codec::now() - 10).unwrap();
        let link = Link::create(None, &dev, "fuzz", "fuzz", Default::default(), aurora_link::codec::now()).unwrap();
        Mutex::new((link, dev))
    })
}

fuzz_target!(|data: &[u8]| {
    let mut buf = data.to_vec();
    let frames = match sync::split(&mut buf) {
        Ok(f) => f,
        Err(_) => match sync::decode(data) {
            Ok(f) => vec![f],
            Err(_) => return,
        },
    };
    let mut guard = fixture().lock().unwrap();
    let (link, dev) = &mut *guard;
    let me = dev.id_hex();
    let mut s = Session::new();
    for f in frames {
        let _ = s.on_frame(link, dev, &me, f.clone(), aurora_link::codec::now());
        let _ = sync::serve_join(link, dev, &me, f, aurora_link::codec::now());
    }
});
