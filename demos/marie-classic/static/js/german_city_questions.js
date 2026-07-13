/**
 * German city competency dropdown for Zaha demo.
 * Loads demos/german_city_competency_questions.json (copied to ./static/data/).
 */
(function () {
    const DATA_URL = "./static/data/german_city_competency_questions.json";
    /** Main TWA city stacks — Pirmasens first (default selection). */
    const CITY_ORDER = ["pirmasens", "bremen", "kaiserslautern"];

    function orderedCityKeys(catalog) {
        return CITY_ORDER.filter((key) => Object.prototype.hasOwnProperty.call(catalog, key));
    }

    function hasMap(spec) {
        return Boolean(spec.map || (spec.parameters && spec.parameters.include_locations));
    }

    async function initGermanCityQuestions() {
        const select = document.getElementById("german-city-select");
        const list = document.getElementById("german-city-question-list");
        if (!select || !list) {
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
            list.innerHTML = `<li>Could not load German city questions (${err}).</li>`;
            return;
        }

        orderedCityKeys(catalog).forEach((key) => {
            const opt = document.createElement("option");
            opt.value = key;
            opt.textContent = (catalog[key] && catalog[key].label) || key;
            select.appendChild(opt);
        });

        function renderQuestions(cityKey) {
            const block = catalog[cityKey] || {};
            const questions = block.questions || [];
            list.replaceChildren();

            questions.forEach((spec) => {
                const li = document.createElement("li");
                const link = document.createElement("a");
                link.href = "#";
                link.textContent = spec.question;
                if (hasMap(spec)) {
                    link.textContent += " (map)";
                }
                link.addEventListener("click", (event) => {
                    event.preventDefault();
                    globalState.set("qa_domain", block.qa_domain || "city");
                    inputField.populateInputText(spec.question);
                    askQuestion();
                });
                li.appendChild(link);
                list.appendChild(li);
            });
        }

        select.addEventListener("change", () => renderQuestions(select.value));
        renderQuestions(select.value);
    }

    document.addEventListener("DOMContentLoaded", initGermanCityQuestions);
})();
