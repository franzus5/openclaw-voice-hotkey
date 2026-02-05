#!/usr/bin/env node

// ACP proxy: stdin JSON -> OpenClaw Gateway -> stdout JSON
// Uses @agentclientprotocol/sdk from OpenClaw's node_modules

import fs from "fs";
import path from "path";
import readline from "readline";
import url from "url";
import WebSocket from "ws";
import { ndJsonStream } from "@agentclientprotocol/sdk/dist/stream.js";
import { AgentSideConnection } from "@agentclientprotocol/sdk/dist/acp.js";

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = __dirname;
const CONFIG_PATH = path.join(ROOT, "config.json");

function loadConfig() {
  const raw = fs.readFileSync(CONFIG_PATH, "utf-8");
  return JSON.parse(raw);
}

async function connectGateway(config) {
  const gatewayUrl = config.gatewayUrl || "ws://127.0.0.1:18789";
  const deviceId = config.deviceId;
  const token = config.gatewayToken;

  if (!deviceId) {
    throw new Error("deviceId missing in config.json (run pairing first)");
  }

  if (!token) {
    throw new Error("gatewayToken missing in config.json (must match gateway.auth.token)");
  }

  const ws = new WebSocket(gatewayUrl);

  const stream = ndJsonStream({
    write: (msg) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(msg + "\n");
      }
    },
    onClose: () => {
      ws.close();
    },
  });

  ws.on("message", (data) => {
    const text = data.toString();
    for (const line of text.split(/\r?\n/)) {
      if (line.trim().length > 0) {
        stream.pushIncoming(line);
      }
    }
  });

  ws.on("close", (code, reason) => {
    console.error("[acp_proxy] WebSocket closed", code, reason.toString());
    process.exit(1);
  });

  ws.on("error", (err) => {
    console.error("[acp_proxy] WebSocket error", err);
    process.exit(1);
  });

  await new Promise((resolve, reject) => {
    ws.once("open", resolve);
    ws.once("error", reject);
  });

  const toAgent = () => ({
    async initialize() {
      return {
        protocolVersion: 1,
        capabilities: {},
      };
    },
    async authenticate() {
      // Not used in this direction
      return {};
    },
    async prompt() {
      throw new Error("prompt not implemented on agent side in proxy");
    },
  });

  const agentConn = new AgentSideConnection(toAgent, stream);

  // Client-side connection to gateway (JSON-RPC over ACP)
  // We use extMethod to call gateway methods.
  const client = agentConn;

  // Send ACP initialize to gateway
  await stream.sendRequest?.("initialize", {
    client: {
      id: "cli",
      version: "1.0.0",
      platform: process.platform,
      mode: "cli",
    },
    role: "operator",
    scopes: ["operator.read", "operator.write"],
    device: {
      id: deviceId,
    },
    auth: {
      token,
    },
  });

  return client;
}

async function run() {
  const config = loadConfig();
  let client;

  try {
    client = await connectGateway(config);
  } catch (err) {
    console.error("[acp_proxy] Failed to connect:", err.message || err);
    process.exit(1);
  }

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false,
  });

  rl.on("line", async (line) => {
    line = line.trim();
    if (!line) return;

    let msg;
    try {
      msg = JSON.parse(line);
    } catch (e) {
      console.error("[acp_proxy] Invalid JSON from stdin:", line);
      return;
    }

    if (msg.type !== "ask") {
      console.error("[acp_proxy] Unsupported message type:", msg.type);
      return;
    }

    const text = msg.text;
    const to = msg.to;
    const channel = msg.channel || "telegram";

    try {
      // Call gateway agent via extMethod
      const res = await client.extMethod("gateway.agent.run", {
        message: text,
        to,
        channel,
      });

      const reply = res?.reply || "";
      process.stdout.write(JSON.stringify({ ok: true, reply }) + "\n");
    } catch (err) {
      process.stdout.write(JSON.stringify({ ok: false, error: String(err) }) + "\n");
    }
  });
}

run().catch((err) => {
  console.error("[acp_proxy] Fatal error:", err);
  process.exit(1);
});
