import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        /**
         * The workspace moved from one screen at /reports/{id} to a three-page
         * flow at /workspace/{id}/…. This redirect is PERMANENT and stays
         * permanently: /reports/{id} URLs are written down outside this
         * codebase -- in screenshots taken against dev.db, in the thesis notes
         * and possibly in the draft itself -- and a 404 on a URL printed in a
         * thesis is not a broken link, it is a broken citation.
         *
         * Only the bare report URL moves. /reports/{id}/explain and
         * /reports/{id}/compare are untouched routes and must keep matching,
         * which is why the source is anchored with no trailing segment.
         */
        source: "/reports/:reportId",
        destination: "/workspace/:reportId/report",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
