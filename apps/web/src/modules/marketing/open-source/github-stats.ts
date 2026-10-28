/** Live repo stats from the GitHub API, cached for an hour. Returns null if GitHub is unreachable. */

export interface RepoStats {
  readonly stars: number;
  readonly forks: number;
  readonly openIssues: number;
  readonly pushedAt: string;
}

interface GitHubRepoResponse {
  readonly stargazers_count: number;
  readonly forks_count: number;
  readonly open_issues_count: number;
  readonly pushed_at: string;
}

export const getRepoStats = async (): Promise<RepoStats | null> => {
  try {
    const response = await fetch(
      "https://api.github.com/repos/balanced7/akashic-aurora",
      {
        headers: { Accept: "application/vnd.github+json" },
        next: { revalidate: 3600 },
        signal: AbortSignal.timeout(4000),
      },
    );
    if (!response.ok) return null;
    const data = (await response.json()) as GitHubRepoResponse;
    return {
      stars: data.stargazers_count,
      forks: data.forks_count,
      openIssues: data.open_issues_count,
      pushedAt: data.pushed_at,
    };
  } catch {
    return null;
  }
};
