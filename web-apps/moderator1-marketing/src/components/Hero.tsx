import Image from "next/image";

export default function Hero() {
  return (
    <div className="section-hero">
      <div className="claim">
        <div className="heading-1">
          <div className="heading-1">
            <span className="add-the-depth-of-an-interview-to-every-survey-you-send-out-0">Add the depth</span>
            <span className="add-the-depth-of-an-interview-to-every-survey-you-send-out-1"> of an interview to every survey you send out</span>
          </div>
        </div>
        <div className="paragraph-lead center">
          Follow up with an AI-moderated interviews with each respondent about their survey responses.
        </div>
      </div>
      <div className="cta-test-drive">
        <div className="frame-24">
          <Image
            src="/images/notification-ringing.svg"
            alt=""
            width={20}
            height={20}
            className="_01-cta-image"
          />
          <div className="text-35">
            <div className="text-35">
              <span className="test-drive-take-this-survey-and-experience-the-moderator1-ai-follow-up-interview-0">Test Drive:</span>
              <span className="test-drive-take-this-survey-and-experience-the-moderator1-ai-follow-up-interview-1"> Take this survey and experience the Moderator1 AI follow-up interview</span>
            </div>
          </div>
        </div>
        <a
          href="https://8il87ey8r6m.typeform.com/to/tYdQm5Bz"
          target="_blank"
          rel="noopener noreferrer"
          className="button-primary-small"
        >
          <div className="button-style-11">Try Now!</div>
        </a>
      </div>
      <div className="lighting-header"></div>
    </div>
  );
}
