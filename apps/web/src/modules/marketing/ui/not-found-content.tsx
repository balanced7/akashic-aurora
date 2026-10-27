import { SignalLost } from "~/modules/marketing/ui/signal-lost";

/** The branded 404, in Aurora's own voice. */
export const NotFoundContent = () => (
  <SignalLost
    code="404 · No record"
    title={
      <>
        Nothing at this address.
        <br />
        <span className="text-mk-muted">Silence beats a weak hint.</span>
      </>
    }
    description="Aurora stays quiet when nothing fits, and so does this page. The link may be old, or the page may have moved."
    command="aurora recall-at --path this/page"
    output="# recall-at-action: nothing relevant (silence beats a weak hint)"
  />
);
