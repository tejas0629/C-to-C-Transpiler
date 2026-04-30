const codeInput = document.getElementById("codeInput");
const sourceLangSelect = document.getElementById("sourceLang");
const targetLangSelect = document.getElementById("targetLang");
const transpileBtn = document.getElementById("transpileBtn");
const sampleBtn = document.getElementById("sampleBtn");
const clearBtn = document.getElementById("clearBtn");
const translatedOutput = document.getElementById("translatedOutput");
const phaseCards = document.getElementById("phaseCards");
const parseTreeContainer = document.getElementById("parseTreeContainer");

const SAMPLES = {
  C: `#include <stdio.h>

int main() {
    int a = 5;
    int b = 10;
    int sum = a + b;
    printf("Sum = %d", sum);
    return 0;
}`,
  "C++": `#include <iostream>
using namespace std;

int main() {
    int x = 10;
    int y = 20;
    std::cout << "Sum: " << (x + y) << std::endl;
    return 0;
}`,
  Java: `public class Main {
    public static void main(String[] args) {
        int num = 42;
        System.out.println("Number: " + num);
    }
}`,
  Python: `def main():
    x = 5
    y = 10
    print("Sum:", x + y)

main()`,
};

clearBtn.addEventListener("click", () => {
  codeInput.value = "";
  translatedOutput.textContent = "";
  phaseCards.innerHTML = "";
  parseTreeContainer.innerHTML = "";
  codeInput.focus();
});

sampleBtn.addEventListener("click", () => {
  const sourceLang = sourceLangSelect.value;
  codeInput.value = SAMPLES[sourceLang] || SAMPLES["C"];
  codeInput.focus();
});

sourceLangSelect.addEventListener("change", () => {
  validateLanguageSelection();
});

targetLangSelect.addEventListener("change", () => {
  validateLanguageSelection();
});

function validateLanguageSelection() {
  const sourceL = sourceLangSelect.value;
  const targetL = targetLangSelect.value;

  if (sourceL === targetL) {
    transpileBtn.disabled = true;
    transpileBtn.title = "Source and target languages must be different";
  } else {
    transpileBtn.disabled = false;
    transpileBtn.title = "";
  }
}

transpileBtn.addEventListener("click", async () => {
  transpileBtn.disabled = true;
  transpileBtn.textContent = "Transpiling...";

  try {
    const sourceL = sourceLangSelect.value;
    const targetL = targetLangSelect.value;

    const response = await fetch("/api/transpile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: codeInput.value,
        source_language: sourceL,
        target_language: targetL,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Failed to transpile code");
    }

    translatedOutput.textContent = data.translated_code;
    renderPhases(data.phases);
    renderParseTree(data.parse_tree);
  } catch (error) {
    translatedOutput.textContent = `Error: ${error.message}`;
    phaseCards.innerHTML = "";
    parseTreeContainer.innerHTML = "";
  } finally {
    transpileBtn.disabled = false;
    transpileBtn.textContent = "Transpile";
    validateLanguageSelection();
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

window.addEventListener("load", () => {
  validateLanguageSelection();
});
