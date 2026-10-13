import { ArrowLeft, FileLock2, Scale, ShieldCheck } from "lucide-react";
import { Link } from "react-router";
import { Brand } from "../../components/Brand";
import { APP_NAME } from "../../config/brand";

const terms = [
  [
    "Use the platform responsibly",
    `Use ${APP_NAME} for lawful, good-faith research. Clearly distinguish sourced facts, personal notes, theories, disputed claims, and AI-assisted synthesis.`,
  ],
  [
    "Share only permitted material",
    "Upload or link only material you own, are authorized to share, or may lawfully use. Do not upload illegal, exploitative, stolen, or malicious files.",
  ],
  [
    "Protect people and investigations",
    "Do not publish private addresses, phone numbers, email addresses, financial data, non-public medical information, or other sensitive personal information.",
  ],
  [
    "Account responsibility",
    `You are responsible for activity through your account and for maintaining the security of your credentials. ${APP_NAME} may restrict or remove accounts and content that violate these terms.`,
  ],
];

const standards = [
  [
    "No harassment or threats",
    "Do not harass, threaten, stalk, intimidate, or organize targeted abuse against any person.",
  ],
  [
    "No doxxing",
    "Do not share private personal information or precise sensitive locations. Respect requests involving safety and privacy.",
  ],
  [
    "Avoid reckless accusations",
    "Do not present a theory, rumor, or AI inference as a verified fact. Do not automatically label real people as suspects or guilty.",
  ],
  [
    "Use sources honestly",
    "Provide links and provenance where possible. Never fabricate sources, alter evidence deceptively, or hide material context.",
  ],
  [
    "No prohibited material",
    "Do not upload illegal content, malware, exploitative imagery, or content that you do not have the right to distribute. Report material that may violate these standards.",
  ],
];

const privacy = [
  [
    "Information we collect",
    `We collect the account and profile information you provide, the cases, messages, files, sources, notes, and other content you submit, and technical records needed to operate and secure ${APP_NAME}.`,
  ],
  [
    "How we use information",
    "We use information to provide accounts and collaboration features, store and display the content you choose to share, perform requested AI-assisted research, prevent abuse, troubleshoot the service, and communicate about your account.",
  ],
  [
    "Google and YouTube data",
    "When an administrator connects a YouTube channel, we use the authorized access only to verify the selected channel and upload requested videos. OAuth credentials are stored as protected application secrets. We do not sell Google user data or use it to train generalized AI models.",
  ],
  [
    "Service providers and disclosure",
    "We share information with hosting, storage, email, authentication, AI, and media-processing providers only as needed to operate the service. We may also disclose information when required by law or to protect users, the public, and the service.",
  ],
  [
    "Public and collaborative content",
    "Cases marked public and contributions made in shared workspaces can be viewed by other people. Review content carefully before publishing it and avoid including private or sensitive personal information.",
  ],
  [
    "Retention and choices",
    "We retain information while it is needed to provide the service, meet legal obligations, resolve disputes, and maintain security. You may update account information and available privacy settings in the application and may request account or data assistance by contacting pabloschall@gmail.com.",
  ],
  [
    "Security and age requirement",
    `We use administrative and technical safeguards designed to protect information, but no online service can guarantee absolute security. ${APP_NAME} accounts are intended for people who are at least 18 years old.`,
  ],
];

const pageContent = {
  terms: {
    title: "Terms of Use",
    description: `These terms establish the basic responsibilities for using ${APP_NAME} as a collaborative public-case research workspace.`,
    sections: terms,
    icon: <Scale size={18} />,
  },
  privacy: {
    title: "Privacy Policy",
    description: `This policy explains how ${APP_NAME} collects, uses, shares, and protects information when you use the service.`,
    sections: privacy,
    icon: <FileLock2 size={18} />,
  },
  standards: {
    title: "Community Standards",
    description: `${APP_NAME} depends on careful sourcing, respect for real people, and collaboration without harassment or reckless accusations.`,
    sections: standards,
    icon: <ShieldCheck size={18} />,
  },
};

export function LegalPage({ kind }: { kind: keyof typeof pageContent }) {
  const content = pageContent[kind];
  return (
    <main className="min-h-dvh bg-paper px-4 py-8 text-primary sm:py-12">
      <div className="mx-auto max-w-3xl">
        <header className="flex items-center justify-between">
          <Brand />
          <Link
            to="/register"
            className="secondary-button min-h-10 px-3 text-xs"
          >
            <ArrowLeft size={14} />
            Registration
          </Link>
        </header>
        <article className="surface mt-8 p-6 sm:p-10">
          <div className="flex items-center gap-2 text-accent">
            {content.icon}
            <p className="eyebrow">Effective October 13, 2026</p>
          </div>
          <h1 className="page-title mt-4">{content.title}</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">
            {content.description}
          </p>
          <div className="mt-8 space-y-6">
            {content.sections.map(([title, body]) => (
              <section key={title} className="border-t border-subtle pt-5">
                <h2 className="section-title">{title}</h2>
                <p className="mt-2 text-sm leading-7 text-secondary">{body}</p>
              </section>
            ))}
          </div>
          {kind !== "privacy" && (
            <div className="mt-8 rounded-lg border border-accent/25 bg-accent-muted p-4 text-xs leading-6 text-secondary">
              By creating an account, you confirm that you are at least 18 years
              old and agree to the current Terms of Use and Community Standards.
              Review our{" "}
              <Link
                to="/privacy"
                className="font-semibold text-accent underline-offset-2 hover:underline"
              >
                Privacy Policy
              </Link>{" "}
              for information about data handling.
            </div>
          )}
        </article>
      </div>
    </main>
  );
}
