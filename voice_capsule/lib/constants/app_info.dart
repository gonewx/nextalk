// 应用信息常量 (版本号、仓库地址)

/// 应用版本号 (构建时通过 --dart-define=APP_VERSION=x.x.x 注入)
const String appVersion = String.fromEnvironment(
  'APP_VERSION',
  defaultValue: 'dev',
);

/// 项目仓库地址
const String appRepoUrl = 'https://github.com/gonewx/nextalk';
