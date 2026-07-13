/* 
------------------------------
Constants
------------------------------
*/

TWA_ABOX_IRI_PREFIXES = ["http://www.theworldavatar.com/kb/", "https://www.theworldavatar.com/kg/"]

/* 
------------------------------
Custom classes
------------------------------
*/

class HttpError extends Error {
    constructor(statusCode, detail = null) {
        super("HTTP error")
        this.statusCode = statusCode
        this.detail = detail
    }

    toString() {
        return `HTTPError (${this.statusCode}): ${this.detail}`
    }
}

/* 
------------------------------
Global states
------------------------------
*/

function defaultQaDomain() {
    const path = (window.location && window.location.pathname) || ""
    if (path.includes("/demos/zaha")) {
        return "singapore"
    }
    if (path.includes("/demos/marie")) {
        return "marie"
    }
    return "marie"
}

const globalState = (function () {
    const states = {
        qa_domain: defaultQaDomain(),
        isProcessing: false,
        chatbotLatency: null,
        err: null
    }
    const watchers = {}

    return {
        get(key) {
            return states[key]
        },
        set(key, val) {
            const oldVal = states[key]
            states[key] = val

            if (key in watchers) {
                watchers[key](oldVal, val)
            }
        },
        registerWatcher(prop, watcher) {
            watchers[prop] = watcher
        }
    }
})()

/* 
------------------------------.
API calls
------------------------------
*/

async function throwErrorIfNotOk(res) {
    if (!res.ok) {
        let detail = null
        try {
            let resJson = await res.json()
            detail = resJson["detail"]
        } catch (_) { }
        throw new HttpError(res.status, detail)
    }
    return res
}

async function fetchQa(question) {
    return fetch("./qa", {
        method: "POST",
        headers: {
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ question, qa_domain: globalState.get("qa_domain") })
    })
        .then(throwErrorIfNotOk)
        .then(res => res.json())
}

/* 
------------------------------
UI Components
------------------------------
*/

function renderDataTable(vars, bindings, parentElem, id) {
    let tableId = id + "-table"
    let content = `<table id=${tableId} class='table table-striped table-bordered' style='width: 100%;'><thead><tr>`

    content += "<th>#</th>"
    vars.forEach(varname => {
        content += `<th>${varname}</th>`
    });
    content += "</tr></thead><tbody>"

    bindings.forEach((valueset, idx) => {
        content += `<tr><td>${idx + 1}</td>`
        vars.forEach(varname => {
            let cell_content = valueset[varname]
            if (typeof valueset[varname] !== "string") {
                cell_content = JSON.stringify(cell_content)
            }
            cell_content = cell_content.replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
            content += `<td>${cell_content}</td>`
        })
        content += "</tr>"
    })

    content += "</tbody></table>"

    let tableContainer = document.createElement("div")
    tableContainer.id = id + "-table-container"
    tableContainer.innerHTML = content;

    let toggleBtn = document.createElement("button")
    toggleBtn.type = "button"
    toggleBtn.className = "btn btn-info"
    toggleBtn.style = "margin-bottom: 1rem;"
    toggleBtn.innerHTML = "Hide IRIs"

    let elem = document.createElement("div")
    elem.id = id
    elem.appendChild(toggleBtn)
    elem.appendChild(tableContainer)

    parentElem.appendChild(elem)

    setTimeout(() => {
        let table = new DataTable('#' + tableId, {
            retrieve: true,
            scrollX: true,
        });

        function toggleShowHideIRI() {
            const rowNum = table.rows().count()
            if (rowNum == 0) {
                return
            }

            let isShowingIRI = toggleBtn.innerHTML === "Hide IRIs"

            const rowData = table.row(0).data()
            const IRIcolIdx = rowData.reduce((arr, val, idx) => {
                if (TWA_ABOX_IRI_PREFIXES.some(prefix => val.startsWith(prefix))) {
                    arr.push(idx)
                }
                return arr
            }, [])
            IRIcolIdx.forEach(colIdx => {
                const col = table.column(colIdx)
                col.visible(!isShowingIRI)
            })

            if (isShowingIRI) {
                toggleBtn.innerHTML = "Show IRIs"
            } else {
                toggleBtn.innerHTML = "Hide IRIs"
            }
        }

        toggleShowHideIRI();

        toggleBtn.addEventListener("click", toggleShowHideIRI)
    }, 0)
}

function renderBootstrapTable(vars, bindings, id, containerElem) {
    let content = `<table id=${id} class='table' style='width: 100%;'><thead><tr>`

    content += "<th>#</th>"
    vars.forEach(varname => {
        content += `<th>${varname}</th>`
    });
    content += "</tr></thead><tbody>"

    bindings.forEach((valueset, idx) => {
        content += `<tr><td>${idx + 1}</td>`
        vars.forEach(varname => {
            let cell_content = valueset[varname]
            if (typeof valueset[varname] !== "string") {
                cell_content = JSON.stringify(cell_content)
            }
            cell_content = cell_content.replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
            content += `<td>${cell_content}</td>`
        })
        content += "</tr>"
    })

    content += "</tbody></table>"
    containerElem.innerHTML = content;
}

function flattenTypedSeries(data, type) {
    if (type === "date") {
        return data.map(x => {
            let date = new Date(x)
            let YYYY = date.getFullYear()
            let MM = date.getMonth() + 1
            let DD = date.getDate()
            let time = date.toLocaleTimeString()
            return `${YYYY}-${MM}-${DD} ${time}`
        })
    } else {
        return data
    }
}

function renderScatterPlot(title, traces, parentElem, id) {
    let plot_traces = traces.map(trace => {
        return {
            type: "scatter",
            name: trace["name"],
            x: flattenTypedSeries(data = trace["x"]["data"], type = trace["x"]["type"]),
            y: flattenTypedSeries(data = trace["y"]["data"], type = trace["y"]["type"])
        }
    })

    let elem = document.createElement("div");
    elem.setAttribute("id", id)
    parentElem.appendChild(elem);

    Plotly.newPlot(id, plot_traces, { title });
}



function renderMap(title, wktText, parentElem, id, wktList) {
    const raster = new ol.layer.Tile({
        source: new ol.source.OSM()
    })

    const format = new ol.format.WKT()
    const wkts = (wktList && wktList.length) ? wktList : [wktText]
    const features = []
    const markerFeatures = []
    wkts.filter(Boolean).forEach((text, idx) => {
        let feature
        try {
            feature = format.readFeature(text, {
                dataProjection: 'EPSG:4326',
                featureProjection: 'EPSG:3857'
            })
        } catch (err) {
            console.warn("Failed to parse WKT for map feature", idx, err)
            return
        }
        features.push(feature)
        // City-scale footprints are often only a few metres across and vanish
        // after fitBounds; add a centroid marker so buildings stay visible.
        const geom = feature.getGeometry()
        if (geom) {
            const extent = geom.getExtent()
            const center = ol.extent.getCenter(extent)
            const marker = new ol.Feature({
                geometry: new ol.geom.Point(center),
                label: String(idx + 1),
            })
            markerFeatures.push(marker)
        }
    })

    const polygonStyle = new ol.style.Style({
        stroke: new ol.style.Stroke({ color: '#c0392b', width: 2 }),
        fill: new ol.style.Fill({ color: 'rgba(231, 76, 60, 0.45)' }),
    })
    const markerStyle = new ol.style.Style({
        image: new ol.style.Circle({
            radius: 7,
            fill: new ol.style.Fill({ color: '#c0392b' }),
            stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 }),
        }),
    })

    const vector = new ol.layer.Vector({
        source: new ol.source.Vector({ features: features }),
        style: polygonStyle,
    })
    const markers = new ol.layer.Vector({
        source: new ol.source.Vector({ features: markerFeatures }),
        style: markerStyle,
    })

    const combined = ol.extent.createEmpty()
    features.forEach(feature => {
        ol.extent.extend(combined, feature.getGeometry().getExtent())
    })
    if (ol.extent.isEmpty(combined)) {
        console.warn("Map has no drawable geometry")
        return
    }

    const centerx = (combined[0] + combined[2]) / 2
    const centery = (combined[1] + combined[3]) / 2

    let elem = document.createElement("div");
    elem.setAttribute("id", id)
    elem.setAttribute("class", "map")
    if (title) {
        const heading = document.createElement("h6")
        heading.textContent = title
        elem.appendChild(heading)
    }
    const mapTarget = document.createElement("div")
    mapTarget.setAttribute("id", id + "-map")
    mapTarget.setAttribute("class", "map")
    mapTarget.style.height = "320px"
    elem.appendChild(mapTarget)
    parentElem.appendChild(elem)

    setTimeout(() => {
        const map = new ol.Map({
            layers: [raster, vector, markers],
            target: id + "-map",
            view: new ol.View({
                center: [centerx, centery],
                zoom: 8,
            }),
        })
        // Padding keeps markers away from the map edge after fit.
        map.getView().fit(combined, {
            size: map.getSize(),
            padding: [40, 40, 40, 40],
            maxZoom: 17,
        })
    }, 0)
}

function renderEmbed(title, url, parentElem, id) {
    let elem = document.createElement("div")
    elem.id = id
    elem.style.marginBottom = "1rem"
    if (title) {
        const heading = document.createElement("h6")
        heading.textContent = title
        elem.appendChild(heading)
    }
    const iframe = document.createElement("iframe")
    iframe.src = url
    iframe.title = title || "Visualisation"
    iframe.style.width = "100%"
    iframe.style.height = "420px"
    iframe.style.border = "1px solid #ddd"
    iframe.setAttribute("loading", "lazy")
    elem.appendChild(iframe)
    parentElem.appendChild(elem)
}

function renderChatbotMarkdown(container, text) {
    if (!text) {
        container.textContent = ""
        return
    }
    if (typeof marked !== "undefined" && typeof DOMPurify !== "undefined") {
        marked.setOptions({ breaks: true, gfm: true })
        const html = marked.parse(text)
        container.innerHTML = DOMPurify.sanitize(html)
    } else {
        container.textContent = text
    }
}

const errorContainer = (function () {
    const elem = document.getElementById("error-container")

    return {
        reset() {
            elem.style.display = "none"
            globalState.set("err", null)
        },

        displayError(message) {
            elem.innerHTML = message
            elem.style.display = "block"
        }
    }
})();

globalState.registerWatcher("err", (_, newVal) => {
    errorContainer.displayError(newVal)
})

const qaMetadataContainer = (function () {
    const elem = document.getElementById("qa-metadata-container")
    const tableContainer = document.getElementById("qa-steps-container")

    function displayQaSteps(steps) {
        renderBootstrapTable(vars = ["action", "arguments", "results", "latency"], bindings = steps, id = "qa-steps-table", containerElem = tableContainer)
        elem.style.display = "block"
    }

    return {
        reset() {
            elem.style.display = "none"
            tableContainer.replaceChildren()
        },

        render(metadata) {
            displayQaSteps(metadata["steps"])
            elem.style.display = "block"
        },
    }
})()

const qaDataContainer = (function () {
    const elem = document.getElementById("qa-data-container")

    return {
        reset() {
            elem.style.display = "none"
            elem.replaceChildren()
        },

        render(data) {
            data.forEach((item, i) => {
                item_type = item["type"]
                id = `data-item-${i}`
                if (item_type === "table") {
                    renderDataTable(vars = item["vars"], bindings = item["bindings"], parentElem = elem, id = id)
                } else if (item_type === "scatter_plot") {
                    renderScatterPlot(title = item["title"], traces = item["traces"], parentElem = elem, id = id)
                } else if (item_type === "map") {
                    renderMap(
                        title = item["title"],
                        wktText = item["wkt_crs84"],
                        parentElem = elem,
                        id = id,
                        wktList = item["wkt_list"]
                    )
                } else if (item_type === "embed") {
                    renderEmbed(title = item["title"], url = item["url"], parentElem = elem, id = id)
                } else {
                    console.log("Unexpected data item: ", item)
                }
            })

            elem.style.display = "block"
        }
    }
})()

const inputField = (function () {
    const elem = document.getElementById('input-field')
    const askButton = document.getElementById('ask-button')

    return {
        populateInputText(text) {
            elem.value = text
            window.scrollTo(0, 0);
        },

        addToInputText(text) {
            const startPos = elem.selectionStart
            const endPos = elem.selectionEnd
            elem.value = elem.value.substring(0, startPos) + text + elem.value.substring(endPos, elem.value.length)
            elem.selectionStart = startPos + text.length
            elem.selectionEnd = startPos + text.length
        },

        disableAsk() {
            askButton.className = "mybutton spinner"
        },

        enableAsk() {
            askButton.className = "mybutton"
        }
    }
})()


const chatbotResponseCard = (function () {
    const elem = document.getElementById("chatbot-response-card")
    const chatbotResponsePara = document.getElementById("chatbot-response")
    const chatbotSpinnerSpan = document.getElementById("chatbot-spinner")
    const chatbotStopAnchor = document.getElementById("chatbot-stop")

    let abortController = new AbortController()
    let streamInterrupted = false
    let streamedText = ""

    async function streamChatbotResponseBodyReader(reader) {
        globalState.set("chatbotLatency", null)
        streamedText = ""

        function pump({ done, value }) {
            if (done) {
                chatbotStopAnchor.style.display = "none"
                renderChatbotMarkdown(chatbotResponsePara, streamedText.trim())
                return;
            }
            // Otherwise do something here to process current chunk
            // format:
            // data: {"content": "abc", "latency": 123}
            // data: {"content": "def", "latency": 456}
            value.split("\n").forEach(line => {
                line = line.trim();
                if (line.startsWith("data: ")) {
                    const msg = line.substring("data: ".length)
                    let datum = null
                    try {
                        datum = JSON.parse(msg)
                    } catch (err) {
                        console.log("Unexpected data received from streaming server:\n".concat(msg))
                    }

                    if (datum !== null) {
                        streamedText += datum["content"]
                        chatbotResponsePara.textContent = streamedText.trimStart()
                        globalState.set("chatbotLatency", datum["latency"])
                    }
                }
            })

            if (streamInterrupted) {
                return reader.cancel()
            } else {
                return reader.read().then(pump)
            }
        }

        return reader.read().then(pump);
    }

    // API calls
    async function fetchChatbotResponseReader(question, data, narrative) {
        const payload = { question, data: JSON.stringify(data) }
        if (narrative) {
            payload.narrative = narrative
        }
        return fetch("./chat", {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload),
            signal: abortController.signal
        })
            .then(throwErrorIfNotOk)
            .then(res => res.body.pipeThrough(new TextDecoderStream()).getReader())
    }

    return {
        reset() {
            elem.style.display = "none"
            chatbotResponsePara.textContent = ""
            streamedText = ""
            chatbotSpinnerSpan.style.display = "inline-block"
            chatbotStopAnchor.style.display = "inline"

            abortController = new AbortController()
            streamInterrupted = false
        },

        async render(question, data, narrative) {
            elem.style.display = "block"
            return fetchChatbotResponseReader(question, data, narrative).then(streamChatbotResponseBodyReader)
        },

        // On-click callbaks
        interruptChatbotStream() {
            streamInterrupted = true
            abortController.abort()
            chatbotSpinnerSpan.style.display = "none"
        },

        hideChatbotSpinner() {
            chatbotSpinnerSpan.style.display = "none"
        }
    }
})()

globalState.registerWatcher("isProcessing", (oldVal, newVal) => {
    if (newVal === oldVal) {
        return
    }

    if (newVal === true) {
        inputField.disableAsk()
    } else {
        inputField.enableAsk()
    }
})

async function askQuestion() {
    if (globalState.get("isProcessing")) { // No concurrent questions
        return;
    }

    const resultSection = document.getElementById("result-section")
    resultSection.style.display = "none"

    const question = document.getElementById("input-field").value;
    if (question === "") {
        return;
    }

    globalState.set("isProcessing", true);

    errorContainer.reset()
    qaMetadataContainer.reset()
    qaDataContainer.reset()
    chatbotResponseCard.reset()

    try {
        const results = await fetchQa(question)
        qaMetadataContainer.render(results["metadata"])
        resultSection.style.display = "block"
        qaDataContainer.render(results["data"])
        chatbotResponseCard.render(question, results["data"], results["narrative"])
    } catch (error) {
        console.log(error.toString())
        if (error instanceof HttpError) {
            if (error.statusCode >= 500 && error.statusCode <= 599) {
                globalState.set("err", "An internal server error is encountered. Please try again.")
            } else if (error.statusCode >= 400 && error.statusCode <= 499) {
                globalState.set("err", error.detail)
            } else {
                globalState.set("err", "An unexpected error is encountered. Please report it with the following error message<br/>" + error)
            }
        } else {
            globalState.set("err", "An unexpected error is encountered. Please report it with the following error message<br/>" + error)
        }
        resultSection.style.display = "block"
    } finally {
        globalState.set("isProcessing", false);
        chatbotResponseCard.hideChatbotSpinner()
    }
}
