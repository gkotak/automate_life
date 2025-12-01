import Image from "next/image";

export default function HowItWorks() {
  return (
    <div id="how-it-works" className="section-process">
      <div className="container">
        <div className="text">
          <div className="badge-green">
            <Image
              src="/images/sparks-alt.svg"
              alt=""
              width={20}
              height={20}
              className="sparks-alt"
            />
            <div className="text-2">How it works</div>
          </div>
          <div className="text-3">
            <div className="text-3">
              <span className="it-takes-a-moment-to-set-up-literally-0">It takes a moment to set up. </span>
              <span className="it-takes-a-moment-to-set-up-literally-1">Literally!</span>
            </div>
          </div>
          <div className="paragraph-lead">No technical skills required.</div>
          <a
            href="https://calendly.com/moderator_1/demo_setup"
            target="_blank"
            rel="noopener noreferrer"
            className="button-primary"
          >
            <div className="button-style-5">Book a demo</div>
          </a>
        </div>
        <div className="timeline-contnet">
          <div className="steps-content">
            {/* Step 1 */}
            <div className="step">
              <div className="timeline-wrapper">
                <div className="timeline-step"></div>
                <div className="timeline-green"></div>
              </div>
              <div className="frame-41">
                <div className="strapline-2">
                  <div className="text-5">01.</div>
                </div>
                <div className="frame-42">
                  <div className="text-6">
                    <span className="add-one-question-to-your-existing-survey-0">Add a webhook </span>
                    <span className="add-one-question-to-your-existing-survey-1">to your survey</span>
                  </div>
                  <div className="ask-the-user-if-they-are-open-to-a-4-minute-voice-interview-as-a-follow-up">
                    This will send Moderator1 the survey responses once the user submits, so that the AI agent can prepare the interview.
                  </div>
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div className="step">
              <div className="timeline-wrapper">
                <div className="timeline-step final-step">
                  <Image src="/images/minicheck.svg" alt="" width={12} height={12} />
                </div>
                <div className="timeline-extra"></div>
              </div>
              <div className="frame-41">
                <div className="strapline-2">
                  <div className="text-5">02.</div>
                </div>
                <div className="frame-42">
                  <div className="text-7">
                    <span className="redirect-to-moderator1-ai-at-the-end-of-your-survey-0">Redirect to Moderator1 AI </span>
                    <span className="redirect-to-moderator1-ai-at-the-end-of-your-survey-1">at the end of your survey</span>
                  </div>
                  <div className="ask-the-user-if-they-are-open-to-a-4-minute-voice-interview-as-a-follow-up">
                    Once users submits the survey, they&apos;ll be taken to Moderator1 to immediately start the voice interview.
                  </div>
                </div>
              </div>
            </div>

            {/* Step 3 (Optional) */}
            <div className="step optional">
              <div className="timeline-wrapper">
                <div className="timeline-step extra"></div>
              </div>
              <div className="frame-41">
                <div className="strapline-3">
                  <div className="text-8">*</div>
                </div>
                <div className="frame-42">
                  <div className="text-6">
                    Guide Moderator1<br />on which topics to focus on (optionally)
                  </div>
                  <div className="text-9">
                    Moderator1 AI works out-of-the-box to interview based on survey responses. But you can give additional instructions.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Process image flow - single combined image */}
      <div className="image-process">
        <Image
          src="/images/process-flow.png"
          alt="Survey flow: Start → Survey Question → Moderator1 Voice Interview"
          width={400}
          height={500}
          className="process-flow-img"
        />
      </div>
    </div>
  );
}
