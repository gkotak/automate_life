import Image from "next/image";

export default function Integrations() {
  return (
    <section className="section-integrations">
      <div className="w-layout-blockcontainer container-2 w-container">
        <div className="text-36">
          <div className="strapline-7">
            <Image
              src="/images/sparks-alt_3.svg"
              alt=""
              width={20}
              height={20}
              className="sparks-alt"
            />
            <div className="text-37">Integrations</div>
          </div>
          <div className="integrates-with-the-survey-tools-you-already-use">
            <div className="integrates-with-the-survey-tools-you-already-use">
              <span className="integrates-with-the-survey-tools-you-already-use-0">Integrates</span>
              <span className="integrates-with-the-survey-tools-you-already-use-1"> with the survey tools you </span>
              <span className="integrates-with-the-survey-tools-you-already-use-0">already</span>
              <span className="integrates-with-the-survey-tools-you-already-use-1"> use.</span>
            </div>
          </div>
        </div>
        <div className="logos-2">
          <div className="frame-69">
            <Image
              src="/images/typeform.png"
              alt="Typeform"
              width={120}
              height={40}
              className="image-5"
            />
            <div className="coming-soon-pill live">
              <div className="coming-soon-label live">Live now!</div>
            </div>
          </div>
          <div className="frame-69">
            <Image
              src="/images/surveysparrow.png"
              alt="SurveySparrow"
              width={120}
              height={40}
              className="image-5 soon"
            />
            <div className="coming-soon-pill">
              <div className="coming-soon-label">Coming soon</div>
            </div>
          </div>
          <div className="frame-69">
            <Image
              src="/images/qualtrics.png"
              alt="Qualtrics"
              width={120}
              height={40}
              className="image-5 soon"
            />
            <div className="coming-soon-pill">
              <div className="coming-soon-label">Coming soon</div>
            </div>
          </div>
          <div className="frame-69">
            <Image
              src="/images/asknicely.png"
              alt="AskNicely"
              width={120}
              height={40}
              className="image-5 soon"
            />
            <div className="coming-soon-pill">
              <div className="coming-soon-label">Coming soon</div>
            </div>
          </div>
          <div className="frame-69">
            <Image
              src="/images/googleforms.png"
              alt="Google Forms"
              width={120}
              height={40}
              className="image-5 soon"
            />
            <div className="coming-soon-pill">
              <div className="coming-soon-label">Coming soon</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
