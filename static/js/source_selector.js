function initSourceSelector() {
    const sourceInput = document.getElementById("source");
    const sourceList = document.getElementById("source-suggestions");
    const sourceIdField = document.getElementById("source_id");
    const clearButton = document.getElementById("clear-source");
    const instructionText = document.getElementById("instruction-text");

    if (!sourceInput || !sourceList || !sourceIdField || !clearButton || !instructionText) {
        return;
    }

    const isHiddenByDefault = window.getComputedStyle(clearButton).display === 'none';

    function sourceBoxFill() {
        if (sourceInput.disabled) {
            sourceList.innerHTML = "";
            return;
        }

        const query = sourceInput.value;

        if (query.length < 1) {
            sourceList.innerHTML = "";
            sourceIdField.value = "";
            return;
        }

        fetch(`/api/search_sources?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                sourceList.innerHTML = "";
                data.forEach(source => {
                    const item = document.createElement("li");
                    item.textContent = source.name;
                    item.dataset.id = source.id;

                    item.addEventListener("click", function () {
                        sourceInput.value = source.name;
                        sourceIdField.value = source.id;
                        sourceList.innerHTML = "";
                        sourceInput.disabled = true;

                        clearButton.disabled = false;
                        if (isHiddenByDefault) {
                            clearButton.style.display = "inline";
                        }

                        instructionText.style.display = "none";
                    });

                    sourceList.appendChild(item);
                });
            });
    }

    sourceInput.addEventListener("click", sourceBoxFill);
    sourceInput.addEventListener("input", sourceBoxFill);

    clearButton.addEventListener("click", function () {
        sourceInput.value = "";
        sourceIdField.value = "";
        sourceInput.disabled = false;

        clearButton.disabled = true;
        if (isHiddenByDefault) {
            clearButton.style.display = "none";
        }

        instructionText.style.display = "block";
    });

    document.addEventListener("click", function (e) {
        if (!sourceList.contains(e.target) && e.target !== sourceInput) {
            sourceList.innerHTML = "";
        }
    });

    // Initial fill if there's already a value
    if (sourceInput.value) {
        sourceBoxFill();
    }
}

document.addEventListener("DOMContentLoaded", initSourceSelector);
