import { Metadata } from "next";
import LegalPageLayout from "@/components/LegalPageLayout";

export const metadata: Metadata = {
  title: "Data Processing Agreement | Moderator1",
  description: "Data Processing Agreement for Moderator1 - AI-moderated follow-up interviews",
};

export default function DataProcessingAgreement() {
  return (
    <LegalPageLayout title="Data Processing Agreement" lastUpdated="July 8, 2025">
      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">1. Introduction</h2>
        <p className="text-gray-700 mb-4">
          This Data Processing Agreement (&quot;DPA&quot;) forms part of the Terms of Service between Tomorrow Tech
          Limited (&quot;Moderator1,&quot; &quot;Processor,&quot; &quot;we,&quot; &quot;us&quot;) and you (&quot;Customer,&quot; &quot;Controller&quot;) and governs
          the processing of personal data in connection with our services.
        </p>
        <p className="text-gray-700 mb-4">
          This DPA is designed to ensure compliance with applicable data protection laws including the
          General Data Protection Regulation (GDPR), UK GDPR, California Consumer Privacy Act (CCPA),
          and the Data Protection Act 2018.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">2. Definitions</h2>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li><strong>&quot;Controller&quot;</strong> means the Customer who determines the purposes and means of processing personal data</li>
          <li><strong>&quot;Processor&quot;</strong> means Moderator1, which processes personal data on behalf of the Controller</li>
          <li><strong>&quot;Personal Data&quot;</strong> means any information relating to an identified or identifiable natural person</li>
          <li><strong>&quot;Data Subject&quot;</strong> means an identifiable natural person whose personal data is processed</li>
          <li><strong>&quot;Sub-processor&quot;</strong> means any third party engaged by the Processor to process personal data</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">3. Roles and Responsibilities</h2>
        <h3 className="font-semibold text-lg mb-3">3.1 Customer Obligations</h3>
        <p className="text-gray-700 mb-4">
          The Customer shall:
        </p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li>Provide Data Subjects with all necessary information about data processing</li>
          <li>Obtain all necessary consents for lawful processing</li>
          <li>Ensure that instructions given to the Processor comply with applicable laws</li>
          <li>Maintain appropriate records of processing activities</li>
        </ul>

        <h3 className="font-semibold text-lg mb-3">3.2 Processor Obligations</h3>
        <p className="text-gray-700 mb-4">
          Moderator1 shall:
        </p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li>Process personal data only for the purposes of the Services and on documented instructions from the Customer</li>
          <li>Ensure that personnel processing personal data are bound by confidentiality obligations</li>
          <li>Implement appropriate technical and organizational security measures</li>
          <li>Assist the Customer in responding to Data Subject requests</li>
          <li>Delete or return personal data upon termination of services</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">4. Data Security</h2>
        <p className="text-gray-700 mb-4">
          Moderator1 implements the following security measures:
        </p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li><strong>Access Control:</strong> Authentication and authorization protocols to restrict access to authorized personnel</li>
          <li><strong>Encryption:</strong> Data encrypted in transit (HTTPS/TLS) and at rest (256-bit AES)</li>
          <li><strong>Just-in-Time Access:</strong> Staff access to customer data is granted only when necessary</li>
          <li><strong>Employee Vetting:</strong> Background checks for employees handling personal data</li>
          <li><strong>Security Assessments:</strong> Regular security audits and vulnerability testing</li>
          <li><strong>Incident Response:</strong> Documented procedures for handling security incidents</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">5. Data Breach Notification</h2>
        <p className="text-gray-700 mb-4">
          In the event of a personal data breach, Moderator1 shall:
        </p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li>Notify the Customer within 48 hours of becoming aware of the breach</li>
          <li>Provide sufficient information to enable the Customer to meet its notification obligations</li>
          <li>Cooperate with the Customer in investigating and mitigating the breach</li>
          <li>Document the breach and remedial actions taken</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">6. Sub-processors</h2>
        <p className="text-gray-700 mb-4">
          Moderator1 uses the following categories of sub-processors:
        </p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li><strong>AWS (Amazon Web Services):</strong> Cloud hosting and infrastructure</li>
          <li><strong>Google Cloud:</strong> AI and machine learning services</li>
          <li><strong>OpenAI:</strong> AI language processing</li>
          <li><strong>Stripe:</strong> Payment processing</li>
        </ul>
        <p className="text-gray-700 mb-4">
          We will provide Customers with at least 7 days&apos; notice before engaging new sub-processors.
          Customers may object to new sub-processors by contacting us within this period.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">7. Data Subject Rights</h2>
        <p className="text-gray-700 mb-4">
          Moderator1 shall assist the Customer in fulfilling its obligations to respond to Data Subject
          requests, including requests for:
        </p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li>Access to personal data</li>
          <li>Rectification of inaccurate data</li>
          <li>Erasure of personal data</li>
          <li>Restriction of processing</li>
          <li>Data portability</li>
          <li>Objection to processing</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">8. Data Protection Impact Assessments</h2>
        <p className="text-gray-700 mb-4">
          Moderator1 shall provide reasonable assistance to the Customer in conducting Data Protection
          Impact Assessments (DPIAs) where required by applicable law.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">9. International Transfers</h2>
        <p className="text-gray-700 mb-4">
          Where personal data is transferred outside the EEA or UK, Moderator1 ensures that appropriate
          safeguards are in place, including Standard Contractual Clauses approved by the European Commission.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">10. Audit Rights</h2>
        <p className="text-gray-700 mb-4">
          Upon reasonable request and subject to confidentiality obligations, Moderator1 shall make
          available to the Customer information necessary to demonstrate compliance with this DPA.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">11. Termination</h2>
        <p className="text-gray-700 mb-4">
          Upon termination of services, Moderator1 shall, at the Customer&apos;s choice, delete or return
          all personal data and delete existing copies, unless retention is required by law.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">12. Contact</h2>
        <p className="text-gray-700 mb-4">
          For questions about this DPA or data processing practices:
        </p>
        <p className="text-gray-700">
          <strong>Email:</strong> privacy@moderator1.com<br />
          <strong>Address:</strong> 43 Manchester Street, London W1U 7LP, United Kingdom
        </p>
      </section>
    </LegalPageLayout>
  );
}
