import { Metadata } from "next";
import LegalPageLayout from "@/components/LegalPageLayout";

export const metadata: Metadata = {
  title: "Privacy Policy | Moderator1",
  description: "Privacy Policy for Moderator1 - AI-moderated follow-up interviews",
};

export default function PrivacyPolicy() {
  return (
    <LegalPageLayout title="Privacy Policy" lastUpdated="July 8, 2025">
      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">1. Introduction</h2>
        <p className="text-gray-700 mb-4">
          This Privacy Policy explains how Tomorrow Tech Limited (&quot;Moderator1,&quot; &quot;we,&quot; &quot;us,&quot; or &quot;our&quot;),
          a company registered in England and Wales (Company No. 10688055), collects, uses, and protects
          your personal information when you use our service.
        </p>
        <p className="text-gray-700 mb-4">
          We are committed to protecting your privacy and handling your data in an open and transparent manner.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">2. Information We Collect</h2>
        <p className="text-gray-700 mb-4">We may collect the following types of personal information:</p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li><strong>Account Information:</strong> Name, email address, job title, company name, and login credentials</li>
          <li><strong>Survey Data:</strong> Responses to surveys, interview recordings, and transcripts</li>
          <li><strong>Contact Information:</strong> Email addresses and phone numbers for communication</li>
          <li><strong>Usage Data:</strong> IP addresses, browser type, device information, and cookies</li>
          <li><strong>Payment Information:</strong> Billing details processed through secure payment providers</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">3. How We Use Your Information</h2>
        <p className="text-gray-700 mb-4">We use your personal information to:</p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li>Provide and maintain our service</li>
          <li>Process and fulfill your requests</li>
          <li>Gather quantitative and qualitative feedback on surveys</li>
          <li>Improve and optimize our platform</li>
          <li>Communicate with you about your account and our services</li>
          <li>Send marketing communications (with your consent)</li>
          <li>Ensure the security and integrity of our service</li>
          <li>Comply with legal obligations</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">4. Sharing Your Information</h2>
        <p className="text-gray-700 mb-4">We may share your personal information with:</p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li><strong>Service Providers:</strong> Third-party vendors who help us operate our service (hosting, analytics, payment processing)</li>
          <li><strong>Group Companies:</strong> Our affiliated companies for business operations</li>
          <li><strong>Professional Advisors:</strong> Lawyers, accountants, and auditors as needed</li>
          <li><strong>Law Enforcement:</strong> When required by law or to protect our rights</li>
          <li><strong>Business Transfers:</strong> In connection with mergers, acquisitions, or asset sales</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">5. Data Security</h2>
        <p className="text-gray-700 mb-4">
          We implement appropriate technical and organizational measures to protect your personal information:
        </p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li>Data encryption in transit using SSL/TLS</li>
          <li>Data encryption at rest using 256-bit AES encryption</li>
          <li>Regular security assessments and audits</li>
          <li>Access controls and authentication mechanisms</li>
          <li>Employee training on data protection</li>
        </ul>
        <p className="text-gray-700 mb-4">
          You are responsible for maintaining the confidentiality of your password and account credentials.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">6. International Data Transfers</h2>
        <p className="text-gray-700 mb-4">
          Your personal data may be transferred to and processed in countries outside the European Economic
          Area (EEA) where data protection laws may differ from those in your country of residence. When
          we transfer data internationally, we ensure appropriate safeguards are in place to protect your
          information.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">7. Your Rights</h2>
        <p className="text-gray-700 mb-4">Under applicable data protection laws, you have the right to:</p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li><strong>Access:</strong> Request a copy of your personal data</li>
          <li><strong>Rectification:</strong> Request correction of inaccurate data</li>
          <li><strong>Erasure:</strong> Request deletion of your personal data</li>
          <li><strong>Restriction:</strong> Request limitation of processing</li>
          <li><strong>Portability:</strong> Request transfer of your data to another service</li>
          <li><strong>Objection:</strong> Object to certain types of processing</li>
          <li><strong>Withdraw Consent:</strong> Withdraw consent for marketing communications</li>
        </ul>
        <p className="text-gray-700 mb-4">
          To exercise these rights, please contact us at privacy@moderator1.com.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">8. Cookies</h2>
        <p className="text-gray-700 mb-4">
          We use cookies and similar technologies to improve your experience, analyze usage patterns,
          and deliver personalized content. You can manage cookie preferences through your browser settings.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">9. Data Retention</h2>
        <p className="text-gray-700 mb-4">
          We retain your personal data only for as long as necessary to fulfill the purposes for which
          it was collected, or as required by law. When data is no longer needed, we securely delete
          or anonymize it.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">10. Children&apos;s Privacy</h2>
        <p className="text-gray-700 mb-4">
          Our service is not intended for individuals under 18 years of age. We do not knowingly collect
          personal information from children.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">11. Changes to This Policy</h2>
        <p className="text-gray-700 mb-4">
          We may update this Privacy Policy from time to time. We will notify you of significant changes
          by updating the &quot;Last updated&quot; date and, where appropriate, by email.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">12. Contact Us</h2>
        <p className="text-gray-700 mb-4">
          If you have any questions about this Privacy Policy or our data practices, please contact us:
        </p>
        <p className="text-gray-700">
          <strong>Email:</strong> privacy@moderator1.com<br />
          <strong>Address:</strong> 43 Manchester Street, London W1U 7LP, United Kingdom
        </p>
      </section>
    </LegalPageLayout>
  );
}
