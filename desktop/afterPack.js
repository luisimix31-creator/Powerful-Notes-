// electron-builder afterPack hook: this build environment tags newly created
// files with extended attributes (com.apple.FinderInfo) that macOS's codesign
// rejects with "resource fork, Finder information, or similar detritus not
// allowed". Strip them from the packaged app before electron-builder signs it.
const { execFileSync } = require("child_process");

exports.default = async function afterPack(context) {
  if (context.electronPlatformName !== "darwin") return;
  const appPath = `${context.appOutDir}/${context.packager.appInfo.productFilename}.app`;
  execFileSync("xattr", ["-cr", appPath]);
};
