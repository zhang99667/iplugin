#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";


const runtimeSource = readFileSync(
  new URL("../../assets/components/interactions/runtime.js", import.meta.url),
  "utf8",
);


class FakeButton {
  constructor(connected = false) {
    this.attributes = new Map();
    this.classes = new Set();
    this.handlers = new Map();
    this.isConnected = connected;
    this.tabIndex = 0;
    this.blurCount = 0;
    this.classList = {
      contains: name => this.classes.has(name),
      toggle: (name, enabled) => {
        if (enabled) this.classes.add(name);
        else this.classes.delete(name);
      },
    };
  }

  get className() {
    return [...this.classes].join(" ");
  }

  set className(value) {
    this.classes = new Set(String(value).split(/\s+/).filter(Boolean));
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }

  addEventListener(type, handler) {
    this.handlers.set(type, handler);
  }

  blur() {
    this.blurCount += 1;
  }
}


function buildEnvironment(existingButton = null) {
  const windowHandlers = new Map();
  const scrollCalls = [];
  let createCount = 0;
  let appendCount = 0;
  let reducedMotion = false;
  const document = {
    activeElement: null,
    querySelector(selector) {
      return selector === ".back-to-top" ? existingButton : null;
    },
    createElement(tag) {
      assert.equal(tag, "button");
      createCount += 1;
      return new FakeButton(false);
    },
    body: {
      appendChild(button) {
        appendCount += 1;
        button.isConnected = true;
        existingButton = button;
      },
    },
  };
  const window = {
    scrollY: 0,
    addEventListener(type, handler) {
      windowHandlers.set(type, handler);
    },
    requestAnimationFrame(handler) {
      handler();
    },
    matchMedia() {
      return { matches: reducedMotion };
    },
    scrollTo(options) {
      scrollCalls.push(options);
    },
  };
  return {
    document,
    window,
    windowHandlers,
    scrollCalls,
    button: () => existingButton,
    createCount: () => createCount,
    appendCount: () => appendCount,
    setReducedMotion(value) {
      reducedMotion = value;
    },
  };
}


function runRuntime(environment) {
  const execute = new Function("window", "document", runtimeSource);
  execute(environment.window, environment.document);
}


// 导出的 HTML 已包含按钮，但事件监听不会被序列化，重新打开时必须复用并重新绑定
const exportedButton = new FakeButton(true);
exportedButton.className = "back-to-top is-visible";
const exported = buildEnvironment(exportedButton);
runRuntime(exported);

assert.equal(exported.window.__HTML_REPORT_INTERACTIONS_READY__, true);
assert.equal(exported.createCount(), 0, "已有动态按钮时不应重复创建");
assert.equal(exported.appendCount(), 0, "已有动态按钮时不应重复插入");
assert.equal(exportedButton.handlers.has("click"), true, "重新打开后必须重新绑定点击事件");
assert.equal(exportedButton.tabIndex, -1, "页面顶部时按钮不应进入 Tab 顺序");
assert.equal(exportedButton.getAttribute("aria-hidden"), "true");
assert.equal(exportedButton.classList.contains("is-visible"), false);

exported.window.scrollY = 500;
exported.windowHandlers.get("scroll")();
assert.equal(exportedButton.classList.contains("is-visible"), true);
assert.equal(exportedButton.tabIndex, 0);
assert.equal(exportedButton.getAttribute("aria-hidden"), "false");

exportedButton.handlers.get("click")();
assert.deepEqual(exported.scrollCalls.at(-1), { top: 0, behavior: "smooth" });
exported.setReducedMotion(true);
exportedButton.handlers.get("click")();
assert.deepEqual(exported.scrollCalls.at(-1), { top: 0, behavior: "auto" });

const boundClick = exportedButton.handlers.get("click");
runRuntime(exported);
assert.equal(exportedButton.handlers.get("click"), boundClick, "同一页面重复执行不能重复绑定");

// 新页面没有按钮时应创建一次并插入 body
const fresh = buildEnvironment();
runRuntime(fresh);
assert.equal(fresh.createCount(), 1);
assert.equal(fresh.appendCount(), 1);
assert.equal(fresh.button().getAttribute("aria-label"), "回到顶部");

console.log("PASS interactions runtime");
