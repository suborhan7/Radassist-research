import { redirect } from "next/navigation";

/**
 * `/workspace/{id}` has no content of its own -- the report is the landing
 * page of the workspace. A server-side redirect rather than a client one, so a
 * deep link never paints an empty frame first.
 */
export default async function WorkspaceIndexPage({
  params,
}: {
  params: Promise<{ reportId: string }>;
}) {
  const { reportId } = await params;
  redirect(`/workspace/${reportId}/report`);
}
