import Header from "@/components/Header";
import Hero from "@/components/Hero";
import Integrations from "@/components/Integrations";
import ValueProps from "@/components/ValueProps";
import HowItWorks from "@/components/HowItWorks";
import UseCases from "@/components/UseCases";
import Pricing from "@/components/Pricing";
import Features from "@/components/Features";
import Tools from "@/components/Tools";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <div className="body">
      <Header />
      <Hero />
      <Integrations />
      <ValueProps />
      <HowItWorks />
      <UseCases />
      <Pricing />
      <Features />
      <Tools />
      <Footer />
    </div>
  );
}
