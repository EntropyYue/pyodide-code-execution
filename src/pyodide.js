async () => {
    // [replace begin]
    let stdout = "";
    let stderr = "";

    let status = "";

    const getPyodide = async (packages) => {
        try {
            await import('/pyodide/pyodide.js');
        }
        catch (err) {
            status = `Error loading Pyodide: ${err}`;
            return {
                stdout: stdout, stderr: stderr, status: status
            };
        }

        const pyodide = await loadPyodide({
            indexURL: '/pyodide/',
            stdout: (text) => {
                stdout += `${text}\n`;
            },
            stderr: (text) => {
                stderr += `${text}\n`;
            },
            packages: ['micropip']
        });

        const mountDir = '/mnt';
        pyodide.FS.mkdirTree(mountDir);

        const micropip = pyodide.pyimport('micropip');
        await micropip.install(packages);

        return pyodide;
    }

    let code = String.raw`[[code]]`;

    let packages = [
        /\bimport\s+requests\b|\bfrom\s+requests\b/.test(code) ? 'requests' : null,
        /\bimport\s+bs4\b|\bfrom\s+bs4\b/.test(code) ? 'beautifulsoup4' : null,
        /\bimport\s+numpy\b|\bfrom\s+numpy\b/.test(code) ? 'numpy' : null,
        /\bimport\s+pandas\b|\bfrom\s+pandas\b/.test(code) ? 'pandas' : null,
        /\bimport\s+matplotlib\b|\bfrom\s+matplotlib\b/.test(code) ? 'matplotlib' : null,
        /\bimport\s+seaborn\b|\bfrom\s+seaborn\b/.test(code) ? 'seaborn' : null,
        /\bimport\s+sklearn\b|\bfrom\s+sklearn\b/.test(code) ? 'scikit-learn' : null,
        /\bimport\s+scipy\b|\bfrom\s+scipy\b/.test(code) ? 'scipy' : null,
        /\bimport\s+re\b|\bfrom\s+re\b/.test(code) ? 'regex' : null,
        /\bimport\s+seaborn\b|\bfrom\s+seaborn\b/.test(code) ? 'seaborn' : null,
        /\bimport\s+sympy\b|\bfrom\s+sympy\b/.test(code) ? 'sympy' : null,
        /\bimport\s+tiktoken\b|\bfrom\s+tiktoken\b/.test(code) ? 'tiktoken' : null,
        /\bimport\s+pytz\b|\bfrom\s+pytz\b/.test(code) ? 'pytz' : null
    ].filter(Boolean);

    try {
        const pyodide = await getPyodide(packages);

        if (code.includes('matplotlib')) {
            // Override plt.show() to return base64 image
            await pyodide.runPythonAsync(String.raw`[[matplotlib_overload]]`);
        }

        await pyodide.runPythonAsync(code);
        status = "OK";
    }
    catch (err) {
        status = `Error running Python code: ${err}`;
    }

    if (stdout.length > 0 && stdout.endsWith('\n')) {
        stdout = stdout.slice(0, -1);
    }
    if (stderr.length > 0 && stderr.endsWith('\n')) {
        stderr = stderr.slice(0, -1);
    }

    return {
        "stdout": stdout, "stderr": stderr, "status": status
    };
    // [replace end]
}
