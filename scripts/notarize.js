/**
 * macOS notarization script — runs after signing (afterSign hook).
 * Set APPLE_ID, APPLE_APP_SPECIFIC_PASSWORD, APPLE_TEAM_ID in environment.
 */
const { notarize } = require("@electron/notarize");

exports.default = async function notarizeApp(context) {
  const { electronPlatformName, appOutDir } = context;

  if (electronPlatformName !== "darwin") return;

  const appleId = process.env.APPLE_ID;
  const appleIdPassword = process.env.APPLE_APP_SPECIFIC_PASSWORD;
  const teamId = process.env.APPLE_TEAM_ID;

  if (!appleId || !appleIdPassword || !teamId) {
    console.warn(
      "[notarize] Skipping notarization — APPLE_ID / APPLE_APP_SPECIFIC_PASSWORD / APPLE_TEAM_ID not set"
    );
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;

  console.log(`[notarize] Notarizing ${appPath} with Apple ID ${appleId}...`);

  await notarize({
    appBundleId: "com.mentis.app",
    appPath,
    appleId,
    appleIdPassword,
    teamId,
  });

  console.log("[notarize] Notarization complete.");
};
