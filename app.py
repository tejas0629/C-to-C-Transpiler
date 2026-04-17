from flask import Flask, jsonify, render_template, request

from transpiler import ParseError, transpile_with_phases

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/transpile", methods=["POST"])
def api_transpile():
    payload = request.get_json(silent=True) or {}
    c_code = payload.get("code", "")

    if not c_code.strip():
        return jsonify({"error": "Please provide C source code before transpiling."}), 400

    try:
        result = transpile_with_phases(c_code)
    except ParseError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({"error": f"Unexpected server error: {exc}"}), 500

    return jsonify(
        {
            "cpp_code": result.cpp_code,
            "parse_tree": result.parse_tree,
            "phases": result.phases,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
