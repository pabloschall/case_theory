import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BadgeArtwork } from "./BadgeArtwork";

describe("BadgeArtwork", () => {
  it.each([
    ["case_file_opened", "/badges/case-file-opened.png"],
    ["source_scout", "/badges/source-scout.png"],
    ["first_connection", "/badges/first-connection.png"],
  ])("maps %s to its production artwork", (badgeCode, expectedPath) => {
    render(
      <BadgeArtwork
        badgeCode={badgeCode}
        badgeName={badgeCode}
        className="badge"
      />,
    );

    expect(screen.getByRole("img", { name: `${badgeCode} badge` })).toHaveAttribute(
      "src",
      expectedPath,
    );
  });
});
