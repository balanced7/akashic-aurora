import { exec } from "child_process";
import { promisify } from "util";

const execPromise = promisify(exec);

export const getLastModifiedAt = async (filePath: string) => {
  try {
    const { stdout } = await execPromise(
      `git log -1 --format=%ai -- ${filePath}`,
    );

    if (stdout) {
      return new Date(stdout.trim()).toISOString();
    }

    return new Date().toISOString();
  } catch {
    return new Date().toISOString();
  }
};
