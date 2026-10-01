const PROXY_CONFIG = [
  {
    context: [
      "/api",
      "/api/**",
      "/static",
      "/static/**",
      "/swagger-ui",
      "/swagger-ui/**"
    ],
    target: "http://18.134.221.206:8080",
    secure: false,
    changeOrigin: true,
    logLevel: "debug"
  },
  {
    context: [
      "/api/ws",
      "/api/ws/**"
    ],
    target: "ws://18.134.221.206:8080",
    ws: true,
    secure: false,
    changeOrigin: true,
    logLevel: "debug"
  }
];

module.exports = PROXY_CONFIG;