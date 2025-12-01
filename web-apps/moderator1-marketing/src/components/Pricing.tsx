import Image from "next/image";

export default function Pricing() {
  return (
    <div id="pricing" className="section-pricing">
      <div className="lighting-pricing"></div>
      <div className="pricing-text">
        <div className="text-17">
          <div className="strapline-5">
            <Image
              src="/images/sparks-alt_1.svg"
              alt=""
              width={20}
              height={20}
              className="sparks-alt"
            />
            <div className="buy-credits-consume-then-refill">
              Buy credits. Consume. Then refill.
            </div>
          </div>
          <div className="text-18">
            <div className="text-18">
              <span className="simple-risk-free-pricing-0">Simple,</span>
              <span className="simple-risk-free-pricing-1"> risk-free pricing</span>
            </div>
          </div>
          <div className="text-19">
            <div className="text-19">
              <span className="only-pay-for-success-with-pricing-per-completed-voice-interview-0">Only pay for success </span>
              <span className="only-pay-for-success-with-pricing-per-completed-voice-interview-1">with pricing per completed voice interview.</span>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="frame-45">
            <div className="text-20">$0.50</div>
            <div className="paragraph-small center">Price per completed voice interview</div>
          </div>
          <div className="frame-47">
            <a
              href="https://calendly.com/moderator_1/demo_setup"
              target="_blank"
              rel="noopener noreferrer"
              className="button-primary"
            >
              <div className="button-style-5">Book a demo</div>
            </a>
            <a
              href="https://8il87ey8r6m.typeform.com/to/tYdQm5Bz"
              target="_blank"
              rel="noopener noreferrer"
              className="button-style-7"
            >
              <div className="link-style-2">Survey walkthrough</div>
            </a>
          </div>
          <div className="frame-46" aria-hidden="true" />
          <div className="frame-48" aria-hidden="true" />
        </div>
        <div className="text-22">Get the first 30 responses on us!</div>
      </div>
    </div>
  );
}
