from flask import Flask, jsonify, render_template, request
import sys

from transpiler import ParseError, transpile_with_phases

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/languages", methods=["GET"])
def api_languages():
    """Return list of supported languages."""
    languages = ["C", "C++", "Java", "Python"]
    return jsonify({"languages": languages})


@app.route("/api/transpile", methods=["POST"])
def api_transpile():
    payload = request.get_json(silent=True) or {}
    input_code = payload.get("code", "")
    source_lang = payload.get("source_language", "C")
    target_lang = payload.get("target_language", "C++")
    
    # Log the parameters
    print(f"[TRANSPILE REQUEST]", file=sys.stderr)
    print(f"  Source Language: {source_lang}", file=sys.stderr)
    print(f"  Target Language: {target_lang}", file=sys.stderr)
    print(f"  Input Code Length: {len(input_code)} chars", file=sys.stderr)
    print(f"  Input Code Preview: {input_code[:100]}...", file=sys.stderr)

    if not input_code.strip():
        return jsonify({"error": "Please provide source code before transpiling."}), 400

    if source_lang == target_lang:
        return jsonify({"error": "Source and target languages must be different."}), 400

    try:
        result = transpile_with_phases(input_code, source_lang, target_lang)
    except ParseError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500

    return jsonify(
        {
            "translated_code": result.translated_code,
            "parse_tree": result.parse_tree,
            "phases": result.phases,
            "source_language": result.source_lang,
            "target_language": result.target_lang,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
