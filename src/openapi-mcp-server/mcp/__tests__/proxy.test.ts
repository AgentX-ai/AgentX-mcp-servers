import { MCPProxy } from "../proxy";
import { OpenAPIV3 } from "openapi-types";
import { HttpClient } from "../../client/http-client";
import type { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";
import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";

// Mock the dependencies
vi.mock("../../client/http-client");
vi.mock("@modelcontextprotocol/sdk/server/index.js");

describe("MCPProxy", () => {
  let proxy: MCPProxy;
  let mockOpenApiSpec: OpenAPIV3.Document;

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();

    // Setup minimal OpenAPI spec for testing
    mockOpenApiSpec = {
      openapi: "3.0.0",
      servers: [{ url: "http://localhost:3000" }],
      info: {
        title: "Test API",
        version: "1.0.0",
      },
      paths: {
        "/test": {
          get: {
            operationId: "getTest",
            responses: {
              "200": {
                description: "Success",
              },
            },
          },
        },
      },
    };

    proxy = new MCPProxy("test-proxy", mockOpenApiSpec);
  });

  describe("listTools handler", () => {
    it("should return converted tools from OpenAPI spec", async () => {
      const server = (proxy as any).server;
      const listToolsHandler = server.setRequestHandler.mock.calls[0].filter(
        (x: unknown) => typeof x === "function"
      )[0];
      const result = await listToolsHandler();

      expect(result).toHaveProperty("tools");
      expect(Array.isArray(result.tools)).toBe(true);
    });

    it("should truncate tool names exceeding 64 characters", async () => {
      // Setup OpenAPI spec with long tool names
      mockOpenApiSpec.paths = {
        "/test": {
          get: {
            operationId: "a".repeat(65),
            responses: {
              "200": {
                description: "Success",
              },
            },
          },
        },
      };
      proxy = new MCPProxy("test-proxy", mockOpenApiSpec);
      const server = (proxy as any).server;
      const listToolsHandler = server.setRequestHandler.mock.calls[0].filter(
        (x: unknown) => typeof x === "function"
      )[0];
      const result = await listToolsHandler();

      expect(result.tools[0].name.length).toBeLessThanOrEqual(64);
    });
  });

  describe("callTool handler", () => {
    it("should execute operation and return formatted response", async () => {
      // Mock HttpClient response
      const mockResponse = {
        data: { message: "success" },
        status: 200,
        headers: new Headers({
          "content-type": "application/json",
        }),
      };
      (
        HttpClient.prototype.executeOperation as ReturnType<typeof vi.fn>
      ).mockResolvedValue(mockResponse);

      // Set up the openApiLookup with our test operation
      (proxy as any).openApiLookup = {
        "API-getTest": {
          operationId: "getTest",
          responses: { "200": { description: "Success" } },
          method: "get",
          path: "/test",
        },
      };

      const server = (proxy as any).server;
      const handlers = server.setRequestHandler.mock.calls
        .flatMap((x: unknown[]) => x)
        .filter((x: unknown) => typeof x === "function");
      const callToolHandler = handlers[1];

      const result = await callToolHandler({
        params: {
          name: "API-getTest",
          arguments: {},
        },
      });

      expect(result).toEqual({
        content: [
          {
            type: "text",
            text: JSON.stringify({ message: "success" }),
          },
        ],
      });
    });

    it("should throw error for non-existent operation", async () => {
      const server = (proxy as any).server;
      const handlers = server.setRequestHandler.mock.calls
        .flatMap((x: unknown[]) => x)
        .filter((x: unknown) => typeof x === "function");
      const callToolHandler = handlers[1];

      await expect(
        callToolHandler({
          params: {
            name: "nonExistentMethod",
            arguments: {},
          },
        })
      ).rejects.toThrow("Method nonExistentMethod not found");
    });

    it("should handle tool names exceeding 64 characters", async () => {
      // Mock HttpClient response
      const mockResponse = {
        data: { message: "success" },
        status: 200,
        headers: new Headers({
          "content-type": "application/json",
        }),
      };
      (
        HttpClient.prototype.executeOperation as ReturnType<typeof vi.fn>
      ).mockResolvedValue(mockResponse);

      // Set up the openApiLookup with a long tool name
      const longToolName = "a".repeat(65);
      const truncatedToolName = longToolName.slice(0, 64);
      (proxy as any).openApiLookup = {
        [truncatedToolName]: {
          operationId: longToolName,
          responses: { "200": { description: "Success" } },
          method: "get",
          path: "/test",
        },
      };

      const server = (proxy as any).server;
      const handlers = server.setRequestHandler.mock.calls
        .flatMap((x: unknown[]) => x)
        .filter((x: unknown) => typeof x === "function");
      const callToolHandler = handlers[1];

      const result = await callToolHandler({
        params: {
          name: truncatedToolName,
          arguments: {},
        },
      });

      expect(result).toEqual({
        content: [
          {
            type: "text",
            text: JSON.stringify({ message: "success" }),
          },
        ],
      });
    });
  });

  describe("getContentType", () => {
    it("should return correct content type for different headers", () => {
      const getContentType = (proxy as any).getContentType.bind(proxy);

      expect(
        getContentType(new Headers({ "content-type": "text/plain" }))
      ).toBe("text");
      expect(
        getContentType(new Headers({ "content-type": "application/json" }))
      ).toBe("text");
      expect(
        getContentType(new Headers({ "content-type": "image/jpeg" }))
      ).toBe("image");
      expect(
        getContentType(
          new Headers({ "content-type": "application/octet-stream" })
        )
      ).toBe("binary");
      expect(getContentType(new Headers())).toBe("binary");
    });
  });

  describe("parseHeadersFromEnv", () => {
    const originalEnv = process.env;

    beforeEach(() => {
      process.env = { ...originalEnv };
    });

    afterEach(() => {
      process.env = originalEnv;
    });

    it("should use NOTION_API_TOKEN and NOTION_VERSION environment variables", () => {
      process.env.NOTION_API_TOKEN = "ntn_test123";
      process.env.NOTION_VERSION = "2022-06-28";

      const proxy = new MCPProxy("test-proxy", mockOpenApiSpec);
      expect(HttpClient).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: {
            Authorization: "Bearer ntn_test123",
            "Notion-Version": "2022-06-28",
          },
        }),
        expect.anything()
      );
    });

    it("should use default Notion version when NOTION_VERSION is not set", () => {
      process.env.NOTION_API_TOKEN = "ntn_test123";
      delete process.env.NOTION_VERSION;

      const proxy = new MCPProxy("test-proxy", mockOpenApiSpec);
      expect(HttpClient).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: {
            Authorization: "Bearer ntn_test123",
            "Notion-Version": "2022-06-28",
          },
        }),
        expect.anything()
      );
    });

    it("should warn when NOTION_API_TOKEN is not set", () => {
      const consoleSpy = vi.spyOn(console, "warn");
      delete process.env.NOTION_API_TOKEN;
      delete process.env.NOTION_VERSION;

      const proxy = new MCPProxy("test-proxy", mockOpenApiSpec);
      expect(HttpClient).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: {
            "Notion-Version": "2022-06-28",
          },
        }),
        expect.anything()
      );
      expect(consoleSpy).toHaveBeenCalledWith(
        "NOTION_API_TOKEN environment variable is not set. API calls may fail."
      );
    });

    it("should fallback to legacy OPENAPI_MCP_HEADERS for backward compatibility", () => {
      process.env.OPENAPI_MCP_HEADERS = JSON.stringify({
        Authorization: "Bearer legacy_token",
        "X-Custom-Header": "test",
      });

      const proxy = new MCPProxy("test-proxy", mockOpenApiSpec);
      expect(HttpClient).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: {
            Authorization: "Bearer legacy_token",
            "X-Custom-Header": "test",
            "Notion-Version": "2022-06-28",
          },
        }),
        expect.anything()
      );
    });

    it("should prioritize new environment variables over legacy ones", () => {
      process.env.NOTION_API_TOKEN = "ntn_new_token";
      process.env.NOTION_VERSION = "2022-06-28";
      process.env.OPENAPI_MCP_HEADERS = JSON.stringify({
        Authorization: "Bearer legacy_token",
        "X-Custom-Header": "test",
      });

      const proxy = new MCPProxy("test-proxy", mockOpenApiSpec);
      expect(HttpClient).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: {
            Authorization: "Bearer ntn_new_token",
            "X-Custom-Header": "test",
            "Notion-Version": "2022-06-28",
          },
        }),
        expect.anything()
      );
    });

    it("should return empty object when no env vars are set", () => {
      delete process.env.NOTION_API_TOKEN;
      delete process.env.NOTION_VERSION;
      delete process.env.OPENAPI_MCP_HEADERS;

      const proxy = new MCPProxy("test-proxy", mockOpenApiSpec);
      expect(HttpClient).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: {
            "Notion-Version": "2022-06-28",
          },
        }),
        expect.anything()
      );
    });

    it("should handle invalid JSON in legacy OPENAPI_MCP_HEADERS", () => {
      const consoleSpy = vi.spyOn(console, "warn");
      process.env.OPENAPI_MCP_HEADERS = "invalid json";

      const proxy = new MCPProxy("test-proxy", mockOpenApiSpec);
      expect(HttpClient).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: {
            "Notion-Version": "2022-06-28",
          },
        }),
        expect.anything()
      );
      expect(consoleSpy).toHaveBeenCalledWith(
        "Failed to parse OPENAPI_MCP_HEADERS environment variable:",
        expect.any(Error)
      );
    });

    it("should handle non-object JSON in legacy OPENAPI_MCP_HEADERS", () => {
      const consoleSpy = vi.spyOn(console, "warn");
      process.env.OPENAPI_MCP_HEADERS = '"string"';

      const proxy = new MCPProxy("test-proxy", mockOpenApiSpec);
      expect(HttpClient).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: {
            "Notion-Version": "2022-06-28",
          },
        }),
        expect.anything()
      );
      expect(consoleSpy).toHaveBeenCalledWith(
        "Failed to parse OPENAPI_MCP_HEADERS environment variable:",
        expect.any(Error)
      );
    });
  });
  describe("connect", () => {
    it("should connect to transport", async () => {
      const mockTransport = {} as Transport;
      await proxy.connect(mockTransport);

      const server = (proxy as any).server;
      expect(server.connect).toHaveBeenCalledWith(mockTransport);
    });
  });
});
