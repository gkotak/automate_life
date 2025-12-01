import { Metadata } from "next";
import LegalPageLayout from "@/components/LegalPageLayout";

export const metadata: Metadata = {
  title: "Terms of Service | Moderator1",
  description: "Terms of Service for Moderator1 - AI-moderated follow-up interviews",
};

export default function TermsOfService() {
  return (
    <LegalPageLayout title="Terms of Service" lastUpdated="July 8, 2025">
      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">1. Agreement to Terms</h2>
        <p className="text-gray-700 mb-4">
          These Terms of Service (&quot;Terms&quot;) govern your access to and use of the Moderator1 service
          operated by Tomorrow Tech Limited (&quot;Company,&quot; &quot;we,&quot; &quot;us,&quot; or &quot;our&quot;), a company registered
          in England and Wales (Company No. 10688055), with its registered office at 43 Manchester Street,
          London W1U 7LP, United Kingdom.
        </p>
        <p className="text-gray-700 mb-4">
          By creating an account or accessing the service, you agree to be bound by these Terms. If you
          do not agree to these Terms, you may not access or use the service.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">2. Changes to Terms</h2>
        <p className="text-gray-700 mb-4">
          We reserve the right to modify these Terms at any time. We will notify you of any changes by
          updating the &quot;Last updated&quot; date at the top of this page. Your continued use of the service
          after any changes constitutes your acceptance of the new Terms.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">3. Eligibility</h2>
        <p className="text-gray-700 mb-4">
          You must be at least 18 years old to use this service. By using the service, you represent
          and warrant that you meet this age requirement.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">4. Account Responsibility</h2>
        <p className="text-gray-700 mb-4">
          You are responsible for maintaining the confidentiality of your account credentials and for
          all activities that occur under your account. You agree to notify us immediately of any
          unauthorized use of your account at support@moderator1.com.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">5. Intellectual Property</h2>
        <p className="text-gray-700 mb-4">
          The service, including all content, features, and functionality, is owned by Tomorrow Tech
          Limited and is protected by international copyright, trademark, and other intellectual
          property laws. You may not copy, modify, or distribute any part of the service without
          our prior written permission.
        </p>
        <p className="text-gray-700 mb-4">
          By using our service, you grant us the right to use your company name and logo on our
          customer lists and marketing materials.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">6. Pricing and Payments</h2>
        <p className="text-gray-700 mb-4">
          All fees are non-refundable. Subscription fees are charged automatically on your billing date.
          We reserve the right to suspend your account for any unpaid fees. You may cancel your
          subscription at any time by contacting support@moderator1.com.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">7. Prohibited Activities</h2>
        <p className="text-gray-700 mb-4">You agree not to:</p>
        <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
          <li>Engage in data scraping or unauthorized automated access</li>
          <li>Use the service for fraudulent or illegal purposes</li>
          <li>Harass, abuse, or harm other users</li>
          <li>Infringe upon intellectual property rights</li>
          <li>Attempt to reverse engineer or compromise the service</li>
          <li>Violate any applicable laws or regulations</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">8. User Content</h2>
        <p className="text-gray-700 mb-4">
          You retain ownership of content you upload to the service. By uploading content, you grant
          us a worldwide, non-exclusive, royalty-free license to use, process, and store your content
          as necessary to provide the service.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">9. Machine Learning</h2>
        <p className="text-gray-700 mb-4">
          We may use anonymized and aggregated data for testing, tuning, optimizing, and validating
          our algorithms. This helps us improve the service for all users.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">10. Termination</h2>
        <p className="text-gray-700 mb-4">
          We may terminate or suspend your account at any time, with or without cause, with or without
          notice. Upon termination, your right to use the service will immediately cease.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">11. Disclaimer of Warranties</h2>
        <p className="text-gray-700 mb-4">
          THE SERVICE IS PROVIDED &quot;AS IS&quot; AND &quot;AS AVAILABLE&quot; WITHOUT WARRANTIES OF ANY KIND, EITHER
          EXPRESS OR IMPLIED. WE DISCLAIM ALL WARRANTIES, INCLUDING IMPLIED WARRANTIES OF MERCHANTABILITY,
          FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">12. Limitation of Liability</h2>
        <p className="text-gray-700 mb-4">
          TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL,
          SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATED TO YOUR USE OF THE SERVICE.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">13. Dispute Resolution</h2>
        <p className="text-gray-700 mb-4">
          Any disputes arising from these Terms shall first be subject to 60 days of good-faith
          negotiation. If unresolved, disputes shall be settled by binding arbitration under the
          LCIA Rules in London, United Kingdom, except for claims involving intellectual property
          rights or injunctive relief.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">14. Governing Law</h2>
        <p className="text-gray-700 mb-4">
          These Terms are governed by and construed in accordance with the laws of the United Kingdom,
          without regard to its conflict of law provisions.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="font-serif text-xl font-bold mb-4">15. Contact Us</h2>
        <p className="text-gray-700 mb-4">
          If you have any questions about these Terms, please contact us at:
        </p>
        <p className="text-gray-700">
          <strong>Email:</strong> support@moderator1.com<br />
          <strong>Address:</strong> 43 Manchester Street, London W1U 7LP, United Kingdom
        </p>
      </section>
    </LegalPageLayout>
  );
}
