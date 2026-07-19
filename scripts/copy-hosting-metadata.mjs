import { copyFile, mkdir } from "node:fs/promises";

const repositoryRoot = new URL("../", import.meta.url);
const source = new URL(".openai/hosting.json", repositoryRoot);
const targetDirectory = new URL("dist/.openai/", repositoryRoot);
const target = new URL("hosting.json", targetDirectory);

try {
  await mkdir(targetDirectory, { recursive: true });
  await copyFile(source, target);
} catch (error) {
  if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") {
    console.warn("Sites metadata is not provisioned yet; skipping hosting.json copy.");
  } else {
    throw error;
  }
}
