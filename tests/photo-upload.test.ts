import { generateKeyPairSync } from "node:crypto";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  MAX_PHOTO_BYTES,
  type Child,
  type UserSession
} from "../src/lib/contracts";
import {
  assertGooglePhotoUploadChild,
  createVerifiedGoogleDrivePhoto,
  PhotoUploadError,
  photoUploadFailureAuditFields,
  resetGoogleTokenCacheForTests,
  uploadGooglePhoto,
  validateDriveFolderMetadata
} from "../src/lib/server/google-workspace";
import { logSafeRouteError } from "../src/lib/server/http";

const originalEnvironment = { ...process.env };
const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const privateKeyPem = privateKey.export({
  type: "pkcs8",
  format: "pem"
}).toString();

const rootFolderId = "root-folder";
const childFolderId = "child-folder";
const sharedDriveId = "shared-drive";

function configureDriveEnvironment(): void {
  process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL =
    "portal@example-project.iam.gserviceaccount.com";
  process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY = privateKeyPem;
  process.env.GOOGLE_DRIVE_SHARED_DRIVE_ID = sharedDriveId;
  process.env.GOOGLE_DRIVE_PHOTOS_FOLDER_ID = rootFolderId;
}

function requestUrl(input: string | URL | Request): URL {
  return new URL(
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url
  );
}

function folderMetadata(id: string, parents?: string[]) {
  return {
    id,
    mimeType: "application/vnd.google-apps.folder",
    trashed: false,
    driveId: sharedDriveId,
    ...(parents ? { parents } : {}),
    capabilities: { canAddChildren: true }
  };
}

const writeSession: UserSession = {
  sessionId: "session-fictional",
  userId: "staff-fictional",
  email: "staff@example.org",
  name: "Test Team",
  role: "staff_write",
  childIds: [],
  sessionVersion: 0,
  issuedAt: 1_700_000_000,
  authSource: "sites",
  expiresAt: 2_000_000_000
};

const fictionalChild: Child = {
  id: "child-fictional",
  name: "Testkind",
  initials: "TK",
  birthDate: "2021-01-01",
  careStart: "2025-01-01",
  group: "Testgruppe",
  status: "active",
  primaryParentId: "parent-fictional",
  primaryParentEmail: "parent@example.org",
  allergies: "",
  dietary: "",
  languagesAtHome: "",
  careHoursPerWeek: 20,
  careFeeCents: 0,
  mealFeeCents: 0,
  photoFolderId: childFolderId,
  photoConsent: "granted",
  downloadConsent: "restricted",
  notesParentVisible: "",
  notesInternal: "",
  updatedAt: "2026-07-30T08:00:00.000Z"
};

describe("Shared Drive photo upload", () => {
  beforeEach(() => {
    configureDriveEnvironment();
    resetGoogleTokenCacheForTests();
  });

  afterEach(() => {
    process.env = { ...originalEnvironment };
    resetGoogleTokenCacheForTests();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("sends a fixed byte-array multipart body and accepts only verified metadata", async () => {
    let uploadBody: Uint8Array | undefined;
    let uploadContentType = "";
    let uploadMetadata: {
      name: string;
      mimeType: string;
      parents: string[];
    } | undefined;

    vi.stubGlobal("fetch", vi.fn(async (
      input: string | URL | Request,
      init?: RequestInit
    ) => {
      const url = requestUrl(input);
      if (url.href === "https://oauth2.googleapis.com/token") {
        return Response.json({ access_token: "test-token", expires_in: 3600 });
      }
      if (url.pathname === `/drive/v3/files/${rootFolderId}`) {
        return Response.json(folderMetadata(rootFolderId));
      }
      if (url.pathname === `/drive/v3/files/${childFolderId}`) {
        return Response.json(folderMetadata(childFolderId, [rootFolderId]));
      }
      if (url.pathname === "/upload/drive/v3/files") {
        expect(init?.method).toBe("POST");
        expect(url.searchParams.get("uploadType")).toBe("multipart");
        expect(url.searchParams.get("supportsAllDrives")).toBe("true");
        expect(url.searchParams.get("fields")).toContain("driveId");
        expect(init?.body).toBeInstanceOf(Uint8Array);
        uploadBody = init?.body as Uint8Array;
        uploadContentType = new Headers(init?.headers).get("content-type") ?? "";
        const text = new TextDecoder().decode(uploadBody);
        const metadataStart = text.indexOf("\r\n\r\n") + 4;
        const metadataEnd = text.indexOf("\r\n--", metadataStart);
        uploadMetadata = JSON.parse(
          text.slice(metadataStart, metadataEnd)
        ) as typeof uploadMetadata;
        return Response.json({
          id: "uploaded-photo",
          name: uploadMetadata?.name,
          mimeType: uploadMetadata?.mimeType,
          createdTime: "2026-07-30T09:00:00.000Z",
          parents: uploadMetadata?.parents,
          driveId: sharedDriveId
        });
      }
      throw new Error(`Unexpected URL host/path: ${url.host}${url.pathname}`);
    }));

    const photo = await createVerifiedGoogleDrivePhoto({
      childId: fictionalChild.id,
      folderId: childFolderId,
      bytes: new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a]),
      mimeType: "image/png",
      now: new Date("2026-07-30T09:00:00.000Z")
    });

    expect(uploadBody).toBeInstanceOf(Uint8Array);
    expect(uploadContentType).toMatch(
      /^multipart\/related; boundary=nine-friends-/u
    );
    expect(uploadMetadata).toMatchObject({
      mimeType: "image/png",
      parents: [childFolderId]
    });
    expect(uploadMetadata?.name).toMatch(
      /^photo_20260730090000_[a-f0-9]{12}\.png$/u
    );
    expect(new TextDecoder().decode(uploadBody)).toContain(
      "Content-Type: image/png\r\nContent-Transfer-Encoding: binary"
    );
    expect(photo).toMatchObject({
      id: "uploaded-photo",
      childId: fictionalChild.id,
      name: uploadMetadata?.name,
      mimeType: "image/png",
      createdAt: "2026-07-30T09:00:00.000Z",
      previewUrl: "/api/photos/uploaded-photo",
      source: "google"
    });
  });

  it("rejects upload metadata that does not confirm the exact parent", async () => {
    vi.stubGlobal("fetch", vi.fn(async (
      input: string | URL | Request,
      init?: RequestInit
    ) => {
      const url = requestUrl(input);
      if (url.href === "https://oauth2.googleapis.com/token") {
        return Response.json({ access_token: "test-token", expires_in: 3600 });
      }
      if (url.pathname === `/drive/v3/files/${rootFolderId}`) {
        return Response.json(folderMetadata(rootFolderId));
      }
      if (url.pathname === `/drive/v3/files/${childFolderId}`) {
        return Response.json(folderMetadata(childFolderId, [rootFolderId]));
      }
      if (url.pathname === "/upload/drive/v3/files") {
        const body = new TextDecoder().decode(init?.body as Uint8Array);
        const metadataStart = body.indexOf("\r\n\r\n") + 4;
        const metadataEnd = body.indexOf("\r\n--", metadataStart);
        const metadata = JSON.parse(body.slice(metadataStart, metadataEnd)) as {
          name: string;
          mimeType: string;
        };
        return Response.json({
          id: "uploaded-photo",
          name: metadata.name,
          mimeType: metadata.mimeType,
          parents: ["wrong-parent"],
          driveId: sharedDriveId
        });
      }
      throw new Error(`Unexpected URL host/path: ${url.host}${url.pathname}`);
    }));

    await expect(createVerifiedGoogleDrivePhoto({
      childId: fictionalChild.id,
      folderId: childFolderId,
      bytes: new Uint8Array([0xff, 0xd8, 0xff, 0x00]),
      mimeType: "image/jpeg"
    })).rejects.toMatchObject({
      status: 502,
      code: "drive_upload_unverified"
    });
  });

  it("rejects a mismatched file signature before contacting Google", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(createVerifiedGoogleDrivePhoto({
      childId: fictionalChild.id,
      folderId: childFolderId,
      bytes: new Uint8Array([0x00, 0x01, 0x02, 0x03]),
      mimeType: "image/jpeg"
    })).rejects.toMatchObject({
      status: 415,
      code: "photo_signature_invalid"
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("enforces the 15 MB limit before contacting Google", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(createVerifiedGoogleDrivePhoto({
      childId: fictionalChild.id,
      folderId: childFolderId,
      bytes: new Uint8Array(MAX_PHOTO_BYTES + 1),
      mimeType: "image/png"
    })).rejects.toMatchObject({
      status: 413,
      code: "photo_too_large"
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("denies upload without current photo consent", () => {
    expect(() => assertGooglePhotoUploadChild({
      ...fictionalChild,
      photoConsent: "withdrawn"
    })).toThrowError(expect.objectContaining({
      status: 403,
      code: "photo_consent_required"
    }));
  });

  it("denies read-only staff without creating a provider or success-audit request", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(uploadGooglePhoto(
      { ...writeSession, role: "staff_read" },
      fictionalChild.id,
      new File(
        [new Uint8Array([0xff, 0xd8, 0xff, 0x00])],
        "fictional.jpg",
        { type: "image/jpeg" }
      )
    )).rejects.toMatchObject({
      status: 403,
      code: "photo_role_forbidden"
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("maps provider failures to sanitized 503 errors", async () => {
    vi.stubGlobal("fetch", vi.fn(async (
      input: string | URL | Request
    ) => {
      const url = requestUrl(input);
      if (url.href === "https://oauth2.googleapis.com/token") {
        return Response.json({ access_token: "test-token", expires_in: 3600 });
      }
      return Response.json({
        error: {
          message: "sensitive provider text with folder identifiers",
          errors: [{ reason: "insufficientFilePermissions" }]
        }
      }, { status: 403 });
    }));

    let caught: unknown;
    try {
      await createVerifiedGoogleDrivePhoto({
        childId: fictionalChild.id,
        folderId: childFolderId,
        bytes: new Uint8Array([0xff, 0xd8, 0xff, 0x00]),
        mimeType: "image/jpeg"
      });
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(PhotoUploadError);
    expect(caught).toMatchObject({
      status: 503,
      code: "drive_provider_unavailable"
    });
    expect(String((caught as Error).message)).not.toMatch(
      /sensitive|folder identifiers|insufficientFilePermissions/iu
    );
  });

  it("rejects a child folder outside the configured root", () => {
    expect(() => validateDriveFolderMetadata(
      folderMetadata(childFolderId, ["different-root"]),
      sharedDriveId,
      rootFolderId
    )).toThrow();
  });

  it("keeps failure audit fields and logs free of provider text and resource IDs", () => {
    const error = new PhotoUploadError(
      503,
      "drive_provider_unavailable",
      "provider text root-folder child-folder"
    );
    expect(photoUploadFailureAuditFields(error, "request-123")).toEqual({
      action: "photo.upload.error.drive_provider_unavailable.503",
      resourceType: "photo",
      outcome: "failure",
      requestId: "request-123"
    });

    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    logSafeRouteError(error, "request-123");
    expect(consoleError).toHaveBeenCalledWith(JSON.stringify({
      status: 503,
      code: "drive_provider_unavailable",
      requestId: "request-123"
    }));
    expect(consoleError.mock.calls.flat().join(" ")).not.toMatch(
      /provider text|root-folder|child-folder/iu
    );
  });
});
