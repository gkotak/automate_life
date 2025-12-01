import Image from "next/image";

export default function Features() {
  return (
    <div className="section-features">
      <div className="frame-55">
        <div className="frame-32">
          <div className="strapline-6">
            <Image
              src="/images/sparks-alt_2.svg"
              alt=""
              width={20}
              height={20}
              className="sparks-alt"
            />
            <div className="text-23">Features</div>
          </div>
          <div className="text-24">
            <div className="text-24">
              <span className="useful-functions-0">Useful,</span>
              <span className="useful-functions-1"> functions</span>
            </div>
          </div>
        </div>
        <div className="frame-52">
          <div className="card-4">
            <Image
              src="/images/Frame-3_3.svg"
              alt=""
              width={40}
              height={40}
              className="frame-72"
            />
            <div className="text-44">
              Works with most survey platforms. <br />5-minute setup.
            </div>
          </div>
          <div className="card-4">
            <Image
              src="/images/Frame-3_5.svg"
              alt=""
              width={40}
              height={40}
              className="frame-72"
            />
            <div className="text-44">Voice AI that works out of the box.</div>
          </div>
          <div className="card-4">
            <Image
              src="/images/Frame-3_6.svg"
              alt=""
              width={40}
              height={40}
              className="frame-72"
            />
            <div className="text-44">
              Set caps or filters on which respondents receive voice interview
            </div>
          </div>
          <div className="card-4">
            <Image
              src="/images/Frame-3_7.svg"
              alt=""
              width={40}
              height={40}
              className="frame-72"
            />
            <div className="text-44">
              Download audio files and transcripts. Import to your survey or BI platform.
            </div>
          </div>
          <div className="card-4">
            <Image
              src="/images/Frame-3_2.svg"
              alt=""
              width={40}
              height={40}
              className="frame-72"
            />
            <div className="text-44">Auto-refill to never run out.</div>
          </div>
          <div className="card-4">
            <Image
              src="/images/Frame-3_4.svg"
              alt=""
              width={40}
              height={40}
              className="frame-72"
            />
            <div className="text-44">
              Optionally, provide guidelines per survey on where to focus.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
