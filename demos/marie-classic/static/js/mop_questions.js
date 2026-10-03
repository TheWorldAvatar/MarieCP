/**
 * MOP polyhedra competency list for Marie demo (remote Blazegraph only).
 */
(function () {
    const DATA_URL = "./static/data/mop_competency_questions.json";

    async function initMopQuestions() {
        const list = document.getElementById("mop-question-list");
        const note = document.getElementById("mop-endpoint-note");
        if (!list) {
            return;
        }

        let catalog = {};
        try {
            const resp = await fetch(DATA_URL);
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            catalog = await resp.json();
        } catch (err) {
            list.innerHTML = `<li>Could not load MOP questions (${err}).</li>`;
            return;
        }

        const block = catalog.ontomops || {};
        if (note && block.endpoint) {
            note.textContent = `Remote SPARQL: ${block.endpoint}`;
        }

        list.replaceChildren();
        (block.questions || []).forEach((spec) => {
            const li = document.createElement("li");
            const link = document.createElement("a");
            link.href = "#";
            link.textContent = spec.question;
            link.addEventListener("click", (event) => {
                event.preventDefault();
                globalState.set("qa_domain", block.qa_domain || "marie");
                inputField.populateInputText(spec.question);
                askQuestion();
            });
            li.appendChild(link);
            list.appendChild(li);
        });
    }

    document.addEventListener("DOMContentLoaded", initMopQuestions);
})();
