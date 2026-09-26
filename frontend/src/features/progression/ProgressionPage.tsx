import { useMutation, useQuery } from "@tanstack/react-query";
import { LockKeyhole } from "lucide-react";
import { PageHeader } from "../../components/ui/Visual";
import { api } from "../../services/api";
import { queryClient } from "../../lib/query";
import { BadgeArtwork } from "./BadgeArtwork";

export function ProgressionPage() {
  const progression = useQuery({
    queryKey: ["progression"],
    queryFn: api.progression,
  });
  const ledger = useQuery({
    queryKey: ["progression", "ledger"],
    queryFn: () => api.progressionLedger(),
  });
  const privacy = useMutation({
    mutationFn: api.updateProgressionPrivacy,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["progression"] }),
  });
  if (progression.isLoading)
    return <p className="eyebrow animate-pulse">Opening field journal</p>;
  if (!progression.data)
    return <p className="error-banner">Progression could not be loaded.</p>;
  const data = progression.data;
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        eyebrow="Field journal"
        title="Research progression."
        description="Earn Research XP by adding structured, sourced work to Case Theory."
      />
      <section className="card mt-8 p-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="eyebrow">Case Theory rank</p>
            <h2 className="mt-2 font-display text-3xl font-semibold text-primary">
              {data.rank.name}
            </h2>
            <p className="mt-1 text-sm text-secondary">
              {data.lifetime_xp.toLocaleString()} lifetime Research XP
            </p>
          </div>
          {data.next_rank && (
            <p className="text-sm text-secondary">
              <strong className="text-primary">
                {data.xp_to_next_rank} XP
              </strong>{" "}
              to {data.next_rank.name}
            </p>
          )}
        </div>
        <div
          className="mt-5 h-2 overflow-hidden rounded-full bg-white/10"
          aria-label={`${data.progress_percent}% progress to next rank`}
        >
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: `${data.progress_percent}%` }}
          />
        </div>
        <div className="mt-5 flex flex-wrap gap-4 border-t border-subtle pt-5 text-sm text-secondary">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={data.show_rank}
              disabled={privacy.isPending}
              onChange={(event) =>
                privacy.mutate({
                  show_rank: event.target.checked,
                  show_badges: data.show_badges,
                })
              }
            />
            Show my rank to signed-in members
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={data.show_badges}
              disabled={privacy.isPending}
              onChange={(event) =>
                privacy.mutate({
                  show_rank: data.show_rank,
                  show_badges: event.target.checked,
                })
              }
            />
            Show my selected badges
          </label>
        </div>
      </section>
      <section className="mt-8">
        <h2 className="section-title">Badge collection</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.badges.map((badge) => {
            const earned = Boolean(badge.earned_at);
            return (
              <article
                key={badge.code}
                className={`card p-5 ${earned ? "border-accent/30" : "opacity-65"}`}
              >
                <div className="relative size-24">
                  <BadgeArtwork
                    badgeCode={badge.code}
                    badgeName={badge.name}
                    className={`size-full object-contain ${earned ? "drop-shadow-[0_0_14px_rgba(213,166,74,.22)]" : "grayscale opacity-30"}`}
                  />
                  {!earned && (
                    <span className="absolute inset-0 grid place-items-center text-muted">
                      <LockKeyhole size={22} />
                    </span>
                  )}
                </div>
                <h3 className="mt-4 font-display text-xl font-semibold text-primary">
                  {badge.name}
                </h3>
                <p className="mt-2 text-sm leading-6 text-secondary">
                  {earned ? badge.description : badge.criteria}
                </p>
                <p className="metadata mt-4">
                  {earned && badge.earned_at
                    ? `Earned ${new Date(badge.earned_at).toLocaleDateString()}`
                    : "Locked"}
                </p>
              </article>
            );
          })}
        </div>
      </section>
      <section className="card mt-8 overflow-hidden">
        <div className="border-b border-subtle p-5">
          <h2 className="section-title">Recent Research XP</h2>
        </div>
        {ledger.isLoading && (
          <p className="p-5 text-sm text-muted">Loading activity…</p>
        )}
        {ledger.data?.items.length === 0 && (
          <p className="p-5 text-sm text-muted">
            Your qualifying research activity will appear here.
          </p>
        )}
        <div className="divide-y divide-subtle">
          {ledger.data?.items.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between gap-4 p-5"
            >
              <div>
                <p className="text-sm font-semibold text-primary">
                  {item.reason}
                </p>
                <p className="metadata mt-1">
                  {new Date(item.created_at).toLocaleString()}
                </p>
              </div>
              <p className="shrink-0 font-semibold text-accent">
                +{item.xp} XP
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
