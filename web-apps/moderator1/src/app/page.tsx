import Link from "next/link";
import { ArrowRight, Check, MessageSquare, BarChart3, Users, Zap } from "lucide-react";

export default function Home() {
    return (
        <div className="min-h-screen flex flex-col font-sans">
            {/* Navigation */}
            <header className="fixed top-0 w-full bg-white/80 backdrop-blur-md z-50 border-b border-slate-200">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <Link href="/" className="text-xl font-bold text-gray-950 flex items-center gap-2">
                        <span className="text-primary-green">Moderator</span>1
                    </Link>
                    <nav className="hidden md:flex items-center gap-8">
                        <Link href="#value" className="text-sm font-medium text-slate-600 hover:text-primary-green transition-colors">
                            Value
                        </Link>
                        <Link href="#how-it-works" className="text-sm font-medium text-slate-600 hover:text-primary-green transition-colors">
                            How it works
                        </Link>
                        <Link href="#pricing" className="text-sm font-medium text-slate-600 hover:text-primary-green transition-colors">
                            Pricing
                        </Link>
                        <Link
                            href="https://calendly.com/moderator_1/demo_setup"
                            target="_blank"
                            className="bg-primary-green text-white px-4 py-2 rounded-full text-sm font-medium hover:bg-[#055a24] transition-colors"
                        >
                            Book a demo
                        </Link>
                    </nav>
                </div>
            </header>

            <main className="flex-grow pt-16">
                {/* Hero Section */}
                <section className="py-20 md:py-32 bg-gradient-to-b from-white to-slate-50">
                    <div className="container mx-auto px-4 text-center max-w-4xl">
                        <h1 className="text-4xl md:text-6xl font-bold text-gray-950 tracking-tight mb-6 leading-tight">
                            Add the depth of an interview to <span className="text-primary-green">every survey</span> you send out
                        </h1>
                        <p className="text-xl text-slate-600 mb-10 max-w-2xl mx-auto leading-relaxed">
                            Follow up with AI-moderated interviews with each respondent about their survey responses.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <Link
                                href="https://8il87ey8r6m.typeform.com/to/tYdQm5Bz"
                                target="_blank"
                                className="w-full sm:w-auto bg-primary-green text-white px-8 py-4 rounded-full text-lg font-semibold hover:bg-[#055a24] transition-all transform hover:scale-105 shadow-lg shadow-primary-green/20 flex items-center justify-center gap-2"
                            >
                                Try Now! <ArrowRight className="w-5 h-5" />
                            </Link>
                            <Link
                                href="https://calendly.com/moderator_1/demo_setup"
                                target="_blank"
                                className="w-full sm:w-auto bg-white text-slate-600 border border-slate-200 px-8 py-4 rounded-full text-lg font-semibold hover:bg-slate-50 transition-all flex items-center justify-center"
                            >
                                Book a Demo
                            </Link>
                        </div>
                    </div>
                </section>

                {/* Value Section */}
                <section id="value" className="py-24 bg-white">
                    <div className="container mx-auto px-4">
                        <div className="grid md:grid-cols-2 gap-16 items-start">
                            <div className="sticky top-32">
                                <h2 className="text-4xl md:text-5xl font-bold text-gray-950 mb-6 leading-tight">
                                    Value<br />
                                    <span className="text-primary-green">Delightful</span> for end users.<br />
                                    <span className="text-primary-green">Deeply insightful</span> for you.
                                </h2>
                                <p className="text-lg text-slate-600">
                                    Follow up with an AI-moderated conversation with each respondent about their survey responses.
                                </p>
                            </div>

                            <div className="grid gap-8">
                                <div className="bg-slate-50 p-8 rounded-2xl border border-slate-100 hover:shadow-lg transition-shadow">
                                    <div className="w-12 h-12 bg-primary-green/10 rounded-xl flex items-center justify-center mb-6">
                                        <MessageSquare className="w-6 h-6 text-primary-green" />
                                    </div>
                                    <h3 className="text-xl font-bold text-gray-950 mb-3">Replace the open-ended question</h3>
                                    <p className="text-slate-600 leading-relaxed">
                                        Let’s face it. Almost no one completes them. They’re annoying and reduce completion rates.
                                    </p>
                                </div>

                                <div className="bg-slate-50 p-8 rounded-2xl border border-slate-100 hover:shadow-lg transition-shadow">
                                    <div className="w-12 h-12 bg-primary-green/10 rounded-xl flex items-center justify-center mb-6">
                                        <Zap className="w-6 h-6 text-primary-green" />
                                    </div>
                                    <h3 className="text-xl font-bold text-gray-950 mb-3">Dive deeper into essential topics</h3>
                                    <p className="text-slate-600 leading-relaxed">
                                        Conversational AI can follow up on multiple questions or topics you’d like additional context on.
                                    </p>
                                </div>

                                <div className="bg-slate-50 p-8 rounded-2xl border border-slate-100 hover:shadow-lg transition-shadow">
                                    <div className="w-12 h-12 bg-primary-green/10 rounded-xl flex items-center justify-center mb-6">
                                        <BarChart3 className="w-6 h-6 text-primary-green" />
                                    </div>
                                    <h3 className="text-xl font-bold text-gray-950 mb-3">Increase completion rates</h3>
                                    <p className="text-slate-600 leading-relaxed">
                                        Users will skip less since the survey is now shorter. Conversational AI can follow up on questions with lower prior responses.
                                    </p>
                                </div>

                                <div className="bg-slate-50 p-8 rounded-2xl border border-slate-100 hover:shadow-lg transition-shadow">
                                    <div className="w-12 h-12 bg-primary-green/10 rounded-xl flex items-center justify-center mb-6">
                                        <Users className="w-6 h-6 text-primary-green" />
                                    </div>
                                    <h3 className="text-xl font-bold text-gray-950 mb-3">Better respondent experience</h3>
                                    <p className="text-slate-600 leading-relaxed">
                                        Survey = boring. Voice calls with an intelligent emotional AI are engaging and convenient.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* How it Works Section */}
                <section id="how-it-works" className="py-24 bg-slate-900 text-white">
                    <div className="container mx-auto px-4">
                        <div className="text-center max-w-3xl mx-auto mb-16">
                            <h2 className="text-3xl md:text-5xl font-bold mb-6">
                                How it works
                            </h2>
                            <p className="text-xl text-slate-300">
                                It takes a moment to set up. Literally! No technical skills required.
                            </p>
                        </div>

                        <div className="grid md:grid-cols-3 gap-8">
                            <div className="bg-slate-800/50 p-8 rounded-2xl border border-slate-700">
                                <div className="text-4xl font-bold text-primary-green mb-6 opacity-50">01</div>
                                <h3 className="text-xl font-bold mb-4">Add a webhook to your survey</h3>
                                <p className="text-slate-400 leading-relaxed">
                                    This will send Moderator1 the survey responses once the user submits, so that the AI agent can prepare the interview.
                                </p>
                            </div>

                            <div className="bg-slate-800/50 p-8 rounded-2xl border border-slate-700">
                                <div className="text-4xl font-bold text-primary-green mb-6 opacity-50">02</div>
                                <h3 className="text-xl font-bold mb-4">Redirect to Moderator1 AI</h3>
                                <p className="text-slate-400 leading-relaxed">
                                    Once users submits the survey, they'll be taken to Moderator1 to immediately start the voice interview.
                                </p>
                            </div>

                            <div className="bg-slate-800/50 p-8 rounded-2xl border border-slate-700">
                                <div className="text-4xl font-bold text-primary-green mb-6 opacity-50">*</div>
                                <h3 className="text-xl font-bold mb-4">Guide Moderator1</h3>
                                <p className="text-slate-400 leading-relaxed">
                                    Moderator1 AI works out-of-the-box to interview based on survey responses. But you can give additional instructions.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Pricing Section */}
                <section id="pricing" className="py-24 bg-white">
                    <div className="container mx-auto px-4 text-center">
                        <h2 className="text-3xl md:text-5xl font-bold text-gray-950 mb-6">
                            Simple Pricing
                        </h2>
                        <p className="text-xl text-slate-600 mb-16 max-w-2xl mx-auto">
                            Start for free, upgrade as you grow.
                        </p>

                        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                            {/* Free Plan */}
                            <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
                                <h3 className="text-2xl font-bold text-gray-950 mb-2">Starter</h3>
                                <div className="text-4xl font-bold text-primary-green mb-6">Free</div>
                                <p className="text-slate-600 mb-8">Perfect for trying out Moderator1.</p>
                                <ul className="text-left space-y-4 mb-8">
                                    <li className="flex items-center gap-3 text-slate-600">
                                        <Check className="w-5 h-5 text-primary-green flex-shrink-0" />
                                        <span>50 interviews / month</span>
                                    </li>
                                    <li className="flex items-center gap-3 text-slate-600">
                                        <Check className="w-5 h-5 text-primary-green flex-shrink-0" />
                                        <span>Basic analytics</span>
                                    </li>
                                    <li className="flex items-center gap-3 text-slate-600">
                                        <Check className="w-5 h-5 text-primary-green flex-shrink-0" />
                                        <span>Email support</span>
                                    </li>
                                </ul>
                                <Link
                                    href="https://8il87ey8r6m.typeform.com/to/tYdQm5Bz"
                                    target="_blank"
                                    className="block w-full bg-slate-100 text-gray-950 py-3 rounded-xl font-semibold hover:bg-slate-200 transition-colors"
                                >
                                    Get Started
                                </Link>
                            </div>

                            {/* Pro Plan */}
                            <div className="bg-gray-950 p-8 rounded-2xl border border-gray-900 shadow-xl text-white relative overflow-hidden">
                                <div className="absolute top-0 right-0 bg-primary-green text-white text-xs font-bold px-3 py-1 rounded-bl-lg">POPULAR</div>
                                <h3 className="text-2xl font-bold mb-2">Pro</h3>
                                <div className="text-4xl font-bold text-primary-green mb-6">Custom</div>
                                <p className="text-slate-400 mb-8">For teams with larger volume.</p>
                                <ul className="text-left space-y-4 mb-8">
                                    <li className="flex items-center gap-3 text-slate-300">
                                        <Check className="w-5 h-5 text-primary-green flex-shrink-0" />
                                        <span>Unlimited interviews</span>
                                    </li>
                                    <li className="flex items-center gap-3 text-slate-300">
                                        <Check className="w-5 h-5 text-primary-green flex-shrink-0" />
                                        <span>Advanced analytics & export</span>
                                    </li>
                                    <li className="flex items-center gap-3 text-slate-300">
                                        <Check className="w-5 h-5 text-primary-green flex-shrink-0" />
                                        <span>Priority support</span>
                                    </li>
                                </ul>
                                <Link
                                    href="https://calendly.com/moderator_1/demo_setup"
                                    target="_blank"
                                    className="block w-full bg-primary-green text-white py-3 rounded-xl font-semibold hover:bg-[#055a24] transition-colors"
                                >
                                    Contact Sales
                                </Link>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Footer */}
                <footer className="py-12 bg-slate-50 border-t border-slate-200">
                    <div className="container mx-auto px-4">
                        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
                            <div className="text-xl font-bold text-gray-950 flex items-center gap-2">
                                <span className="text-primary-green">Moderator</span>1
                            </div>
                            <div className="flex gap-6 text-sm text-slate-500">
                                <Link href="/terms" className="hover:text-primary-green transition-colors">Terms</Link>
                                <Link href="/privacy" className="hover:text-primary-green transition-colors">Privacy</Link>
                                <Link href="mailto:support@moderator1.com" className="hover:text-primary-green transition-colors">Contact</Link>
                            </div>
                            <div className="text-sm text-slate-400">
                                © {new Date().getFullYear()} Moderator1. All rights reserved.
                            </div>
                        </div>
                    </div>
                </footer>
            </main>
        </div>
    );
}
