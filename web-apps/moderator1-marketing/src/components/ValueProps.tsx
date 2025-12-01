import Image from "next/image";

export default function ValueProps() {
  return (
    <div id="values" className="section-values">
      <div className="text-39">
        <div className="badge-green">
          <Image
            src="/images/sparks-alt_3.svg"
            alt=""
            width={20}
            height={20}
            className="sparks-alt"
          />
          <div className="text-40">Value</div>
        </div>
        <div className="heading-2">
          <div className="heading-2">
            <span className="delightful-for-end-users-deeply-insightful-for-you-0">Delightful</span>
            <span className="delightful-for-end-users-deeply-insightful-for-you-1"> for end users. Deeply </span>
            <span className="delightful-for-end-users-deeply-insightful-for-you-0">insightful</span>
            <span className="delightful-for-end-users-deeply-insightful-for-you-1"> for you.</span>
          </div>
        </div>
        <div className="paragraph-lead center">
          Follow up with an AI-moderated conversation with each respondent about their survey responses
        </div>
      </div>
      <div className="grid-2">
        {/* Card 1: Replace the open-ended question */}
        <div className="card-3">
          <Image
            src="/images/boost.svg"
            alt=""
            width={32}
            height={32}
            className="frame-70"
          />
          <div className="frame-35">
            <div className="heading-5">
              <div className="heading-5">
                <span className="boost-the-open-ended-question-0">Replace</span>
                <span className="boost-the-open-ended-question-1"> the open-ended question</span>
              </div>
            </div>
            <div className="paragraph-small">
              Let&apos;s face it. Almost no one completes them. They&apos;re annoying and reduce completion rates.
            </div>
          </div>
          <Image
            src="/images/Image2x.png"
            alt=""
            width={516}
            height={300}
            className="image-6"
          />
        </div>

        {/* Card 2: Dive deeper into essential topics */}
        <div className="card-3">
          <Image
            src="/images/dive.svg"
            alt=""
            width={32}
            height={32}
            className="frame-70"
          />
          <div className="frame-35">
            <div className="heading-5">
              <div className="heading-5">
                <span className="boost-the-open-ended-question-0">Dive deeper</span>
                <span className="boost-the-open-ended-question-1"> into essential topics</span>
              </div>
            </div>
            <div className="paragraph-small">
              Converational AI can follow up on multiple questions or topics you&apos;d like additional context on.
            </div>
          </div>
          <Image
            src="/images/dive-deeper2x.png"
            alt=""
            width={516}
            height={300}
            className="image-6"
          />
        </div>

        {/* Card 3: Increase completion rates */}
        <div className="card-3">
          <Image
            src="/images/Frame-3_1.svg"
            alt=""
            width={32}
            height={32}
            className="frame-70"
          />
          <div className="frame-35">
            <div className="heading-5">
              <div className="heading-5">
                <span className="boost-the-open-ended-question-0">Increase</span>
                <span className="boost-the-open-ended-question-1"> completion rates</span>
              </div>
            </div>
            <div className="paragraph-small">
              Users will skip less since the survey is now shorter. Conversational AI can follow up on questions with lower prior responses.
            </div>
          </div>
          <Image
            src="/images/increase0completion-rates2x_1.avif"
            alt=""
            width={516}
            height={300}
            className="image-6"
          />
        </div>

        {/* Card 4: Better respondent experience */}
        <div className="card-3">
          <Image
            src="/images/Frame-3.svg"
            alt=""
            width={32}
            height={32}
            className="frame-70"
          />
          <div className="frame-35">
            <div className="heading-5">
              <div className="heading-5">
                <span className="boost-the-open-ended-question-0">Better</span>
                <span className="boost-the-open-ended-question-1"> respondent experience</span>
              </div>
            </div>
            <div className="paragraph-small">
              Survey = boring. Voice calls with an intelligent emotional AI are engaging and convenient.
            </div>
          </div>
          <Image
            src="/images/make-your-users-love-it2x.png"
            alt=""
            width={516}
            height={300}
            className="image-6"
          />
        </div>
      </div>

      {/* Sounds great section */}
      <div className="waitlist-section">
        <div className="text-43">
          <div className="text-43">
            <span className="sounds-great-isnt-it-0">Sounds</span>
            <span className="sounds-great-isnt-it-1"> </span>
            <span className="highligher">great</span>
            <span className="sounds-great-isnt-it-0">, doesn&apos;t it?</span>
          </div>
        </div>
        <a
          href="https://calendly.com/moderator_1/demo_setup"
          target="_blank"
          rel="noopener noreferrer"
          className="button-secondary b-w w-button"
        >
          Book a Demo
        </a>
      </div>
      <div className="wishlist-background"></div>
    </div>
  );
}
