const cCodeInput = document.getElementById("cCodeInput");
const transpileBtn = document.getElementById("transpileBtn");
const sampleBtn = document.getElementById("sampleBtn");
const cppOutput = document.getElementById("cppOutput");
const phaseCards = document.getElementById("phaseCards");
const parseTreeContainer = document.getElementById("parseTreeContainer");

const ADVANCED_SAMPLE = `#include <stdio.h>

int factorial(int n) {
    int result = 1;
    for (int i = 1; i <= n; i = i + 1) {
        result = result * i;
    }
    return result;
}

int main() {
    int n = 5;
    int out = factorial(n);
    printf("Factorial = %d", out);
    return 0;
}`;

sampleBtn.addEventListener("click", () => {
  cCodeInput.value = ADVANCED_SAMPLE;
  cCodeInput.focus();
});

transpileBtn.addEventListener("click", async () => {
  transpileBtn.disabled = true;
  transpileBtn.textContent = "Compiling...";

  try {
    const response = await fetch("/api/transpile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: cCodeInput.value }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Failed to transpile code");
    }

    cppOutput.textContent = data.cpp_code;
    renderPhases(data.phases);
    renderParseTree(data.parse_tree);
  } catch (error) {
    cppOutput.textContent = `Error: ${error.message}`;
    phaseCards.innerHTML = "";
    parseTreeContainer.innerHTML = "";
  } finally {
    transpileBtn.disabled = false;
    transpileBtn.textContent = "Run 7-Phase Transpiler";
  }
});

function renderPhases(phases) {
  phaseCards.innerHTML = "";

  Object.entries(phases).forEach(([name, value], idx) => {
    const card = document.createElement("article");
    card.className = "phase-card";
    card.style.animationDelay = `${idx * 80}ms`;

    const title = document.createElement("h3");
    title.textContent = name.replaceAll("_", " ");

    const details = document.createElement("pre");
    details.textContent = JSON.stringify(value, null, 2);

    card.appendChild(title);
    card.appendChild(details);
    phaseCards.appendChild(card);
  });
}

function renderParseTree(tree) {
  parseTreeContainer.innerHTML = "";
  parseTreeContainer.appendChild(makeTreeNode(tree));
}

function makeTreeNode(node) {
  const wrapper = document.createElement("div");
  wrapper.className = "tree-node";

  const label = document.createElement("span");
  label.className = "tree-label";
  label.textContent = makeNodeLabel(node);
  wrapper.appendChild(label);

  const children = extractChildren(node);
  if (children.length) {
    const childWrap = document.createElement("div");
    childWrap.className = "tree-children";
    children.forEach((child) => childWrap.appendChild(makeTreeNode(child)));
    wrapper.appendChild(childWrap);

    label.addEventListener("click", () => {
      wrapper.classList.toggle("collapsed");
    });
  }

  return wrapper;
}

function makeNodeLabel(node) {
  const t = node.type || "Node";
  const importantKeys = ["name", "varType", "returnType", "operator", "value", "callee"];
  const tags = importantKeys
    .filter((key) => node[key] !== undefined && typeof node[key] !== "object")
    .map((key) => `${key}:${node[key]}`)
    .join(" | ");
  return tags ? `${t} (${tags})` : t;
}

function extractChildren(node) {
  const children = [];
  Object.values(node).forEach((value) => {
    if (!value) return;
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item && typeof item === "object") children.push(item);
      });
    } else if (typeof value === "object" && value.type) {
      children.push(value);
    }
  });
  return children;
}

window.dispatchEvent(new Event("load"));
