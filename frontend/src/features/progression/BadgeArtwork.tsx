import { Award } from "lucide-react";

const badgeAssets: Record<string, string> = {
  first_citation: "/badges/first-citation.png",
  timeline_builder: "/badges/timeline-builder.png",
  evidence_curator: "/badges/evidence-curator.png",
};

export function BadgeArtwork({
  badgeCode,
  badgeName,
  className,
}: {
  badgeCode: string;
  badgeName: string;
  className: string;
}) {
  const src = badgeAssets[badgeCode];
  if (!src) return <Award className={className} aria-hidden="true" />;
  return <img src={src} alt={`${badgeName} badge`} className={className} />;
}
