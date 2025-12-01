import Image from "next/image";
import Link from "next/link";

export default function Footer() {
  return (
    <div className="section-footer">
      <div className="footer">
        <div className="frame-64">
          <div className="frame-62">
            <Image
              src="/images/image-11.png"
              alt="Moderator1"
              width={140}
              height={40}
              className="image-11"
            />
            <div className="text-28">
              Add the depth of an interview to every survey you send out.
            </div>
          </div>
        </div>
        <div className="frame-60">
          <div className="_2025-moderator1-all-rights-reserved">
            &copy; 2025 Moderator1 All Rights Reserved
          </div>
          <div className="frame-63">
            <Link href="/terms-of-service" className="link-block w-inline-block">
              <div className="text-31">Terms &amp; Conditions</div>
            </Link>
            <Link href="/privacy-policy" className="link-block-2 w-inline-block">
              <div className="text-31">Privacy Policy</div>
            </Link>
            <Link href="/data-processing-agreement" className="link-block-3 w-inline-block">
              <div className="text-31">Data Processing Agreement</div>
            </Link>
            <a href="mailto:support@moderator1.com" className="link-block-4 w-inline-block">
              <div className="text-31">Contact</div>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
