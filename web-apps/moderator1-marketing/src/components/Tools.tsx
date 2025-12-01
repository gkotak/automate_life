"use client";

import Image from "next/image";
import { useState } from "react";

export default function Tools() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // In production, integrate with email service
    setSubmitted(true);
  };

  return (
    <div className="tools">
      <div className="paragraph-small center">
        <span>
          <strong className="text-15">Be the first to know when we support your survey tool</strong>
        </span>
      </div>
      <div className="form-newsletter w-form">
        {!submitted ? (
          <form
            id="email-form-2"
            name="email-form-2"
            className="form-2"
            onSubmit={handleSubmit}
          >
            <input
              className="text-field-2 w-input"
              maxLength={256}
              name="email"
              placeholder="Type your e-mail address"
              type="email"
              id="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input
              type="submit"
              className="button-primary-small w-button"
              value="Subscribe"
            />
          </form>
        ) : (
          <div className="form-newsletter---success w-form-done">
            <div>Thank you! Your submission has been received!</div>
          </div>
        )}
      </div>
      <div className="div-block-4">
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
      <div className="frame-61"></div>
    </div>
  );
}
