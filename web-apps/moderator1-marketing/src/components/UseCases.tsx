import Image from "next/image";

export default function UseCases() {
  return (
    <div id="use-cases" className="section-whos-it-for">
      <div className="heading">
        <div className="strapline-4">
          <Image
            src="/images/sparks-alt.svg"
            alt=""
            width={20}
            height={20}
            className="sparks-alt"
          />
          <div className="text-12">Use Cases</div>
        </div>
        <div className="text-13">Who&apos;s it for</div>
        <div className="paragraph-lead">
          Anyone who conducts a survey and wants to add in-depth insights to have more confidence in your decisions. these include:
        </div>
      </div>
      <div className="grid">
        {/* Market Research Surveys */}
        <div className="market-research-surveys">
          <div className="w-layout-vflex flex-block-2">
            <Image
              src="/images/icon_MarketResearch.svg"
              alt=""
              width={48}
              height={48}
              className="frame-3"
            />
            <div className="text-15">Market Research Surveys</div>
            <div className="paragraph-small">
              Add the depth of panel interviews to all your market research surveys.
            </div>
          </div>
        </div>

        {/* Customer Surveys */}
        <div className="market-research-surveys">
          <div className="div-block-3">
            <Image
              src="/images/icon_CustomerSurveys.svg"
              alt=""
              width={48}
              height={48}
              className="frame-3"
            />
            <div className="text-15">Customer Surveys</div>
            <div className="paragraph-small">
              Get the true &apos;voice of customer&apos;. Understand the &apos;why&apos; behind positive or negative CSAT and NPS scores.
            </div>
          </div>
        </div>

        {/* Win/loss/churn interviews */}
        <div className="market-research-surveys">
          <div className="div-block-3">
            <Image
              src="/images/icon_WinLossInterviews.svg"
              alt=""
              width={48}
              height={48}
              className="frame-3"
            />
            <div className="text-15">Win/loss/churn interviews</div>
            <div className="paragraph-small">
              Uncover the real reasons you win and lose deal, and why your customer churns
            </div>
          </div>
        </div>

        {/* Employee Surveys */}
        <div className="market-research-surveys">
          <div className="div-block-3">
            <Image
              src="/images/icon_EmployeeSurveys.svg"
              alt=""
              width={48}
              height={48}
              className="frame-3"
            />
            <div className="text-15">Employee Surveys</div>
            <div className="paragraph-small">
              Get more detailed insights from your employee engagement surveys
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
