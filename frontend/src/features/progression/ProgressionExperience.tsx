import { useMutation, useQuery } from "@tanstack/react-query";
import { Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import type { ProgressionBadge } from "../../types";
import { queryClient } from "../../lib/query";
import { api } from "../../services/api";
import { BadgeArtwork } from "./BadgeArtwork";

export function ProgressionExperience({ enabled }: { enabled: boolean }) {
  const [receiptVisible, setReceiptVisible] = useState(false);
  const progression = useQuery({
    queryKey: ["progression"],
    queryFn: api.progression,
    enabled,
    retry: false,
    refetchInterval: 8_000,
  });
  const badge = progression.data?.pending_badges[0];
  const receipt = progression.data?.pending_receipts[0];
  const acknowledge = useMutation({
    mutationFn: api.acknowledgeProgression,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["progression"] }),
  });

  useEffect(() => {
    if (!receipt || badge) return;
    setReceiptVisible(true);
    const hide = window.setTimeout(() => {
      setReceiptVisible(false);
      acknowledge.mutate({ receipt_ids: [receipt.id] });
    }, 4_500);
    return () => window.clearTimeout(hide);
  }, [receipt?.id, badge?.code]); // eslint-disable-line react-hooks/exhaustive-deps

  const dismissBadge = () => {
    if (!badge || acknowledge.isPending) return;
    acknowledge.mutate({ badge_codes: [badge.code] });
  };

  return (
    <>
      {badge && (
        <AchievementReveal
          badge={badge}
          onDismiss={dismissBadge}
          pending={acknowledge.isPending}
        />
      )}
      {receipt && receiptVisible && !badge && (
        <div
          role="status"
          className="fixed bottom-24 right-4 z-40 max-w-sm animate-[achievement-in_.35s_ease-out] rounded-xl border border-accent/35 bg-surface px-4 py-3 shadow-2xl motion-reduce:animate-none md:bottom-6 md:right-6"
        >
          <p className="text-sm font-semibold text-accent">
            +{receipt.xp} Research XP
          </p>
          <p className="mt-1 text-xs text-secondary">{receipt.reason}</p>
        </div>
      )}
    </>
  );
}

function AchievementReveal({
  badge,
  onDismiss,
  pending,
}: {
  badge: ProgressionBadge;
  onDismiss: () => void;
  pending: boolean;
}) {
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="achievement-title"
    >
      <div className="achievement-card relative w-full max-w-md overflow-hidden rounded-2xl border border-accent/45 bg-surface p-7 text-center shadow-2xl motion-reduce:animate-none">
        <button
          type="button"
          onClick={onDismiss}
          disabled={pending}
          className="ghost-button absolute right-3 top-3 size-10 px-0"
          aria-label="Close achievement"
        >
          <X size={18} />
        </button>
        <div className="mx-auto size-36 drop-shadow-[0_0_28px_rgba(213,166,74,.3)] sm:size-44">
          <BadgeArtwork
            badgeCode={badge.code}
            badgeName={badge.name}
            className="size-full object-contain"
          />
        </div>
        <p className="eyebrow mt-6 flex items-center justify-center gap-2">
          <Sparkles size={13} />
          Achievement unlocked
        </p>
        <h2
          id="achievement-title"
          className="mt-2 font-display text-3xl font-semibold text-primary"
        >
          {badge.name}
        </h2>
        <p className="mx-auto mt-3 max-w-sm text-sm leading-6 text-secondary">
          {badge.description}
        </p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
          <Link
            to="/progression"
            onClick={onDismiss}
            className="primary-button"
          >
            View badges
          </Link>
          <button
            type="button"
            onClick={onDismiss}
            disabled={pending}
            className="secondary-button"
          >
            Continue researching
          </button>
        </div>
      </div>
    </div>
  );
}
