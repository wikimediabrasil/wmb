let dates = [];
let titles = [];
let titlesH = [];
let datesS = [];
let w;
let total_boxes = 0;
let monthColor;

function downloadCalendar(e) {
    e.preventDefault();

    const activityData = e.target;
    w = window.open("", "_blank");
    getActivityData(activityData);
    getMonthValues();
    addHTML(w);
    save(w);
    return false;
}

function getMonthValues() {
    const monthColors = {
        janeiro: "#000000",
        fevereiro: "#5f174a",
        marco: "#242856",
        março: "#242856",
        abril: "#2c70b7",
        maio: "#23772d",
        junho: "#e6520f",
        julho: "#c10248",
        agosto: "#016668",
        setembro: "#f9b215",
        outubro: "#d81d61",
        novembro: "#18499a",
        dezembro: "#cc1517"
    };
    monthColor = monthColors[month] || "#000000";
}

/* Receives an activityData object. Extracts the date and title from it, and adds them to their respective global variables. */
function getActivityData(activityData) {
    dates = [];
    titles = [];
    let i = 1;
    while (activityData.has(`date_${i}`)) {
        if (activityData.get(`date_${i}`)) {
            dates.push(activityData.get(`date_${i}`));
        }
        if (activityData.get(`info_${i}`)) {
            titles.push(activityData.get(`info_${i}`));
        }
        i++;
    }

    total_boxes = dates.length;
}

/* Receives a window and generates the HTML to it. */
function addHTML(w) {
    try {
        header(w);
        calculateDateFontSize();
        addBoxes(w);
        footer(w);
    } catch (error) {
        console.error("Error generating calendar:", error);
        w.document.write("<div class='evento' style='color:white; font-size:30px'>Algo deu errado. (Provavelmente você preencheu um campo de data de um evento e deixou o título do mesmo em branco.)</div>");
    }
}

/* Calculates the font size of the date field. */
function calculateDateFontSize() {
    datesS = dates.map(date => date.length < 5 ? "33pt" : "22pt");
}

function header(w) {
    w.document.write(`
    <html lang="pt">
        <head>
            <title>Calendário</title>
            <link rel="stylesheet" type="text/css" href="${static_url}css/calendar.css">
        </head>
        <body style="padding: 0;margin: 0">
        <div class='w3-container'>
            <div id="canvas-container" style="background-image: url('${media_url}month_calendars/${month}.png')">
                <div class='calendar-main'>
    `);
}

/* Receives a window and adds each event div to it, along with its respective titlesH (titles height) and datesS (date font-size) style modifiers. */
function addBoxes(w) {
    dates.forEach((date, i) => {
        addBox(w, date, titles[i], titlesH[i], datesS[i]);
    });
}

/* Receives a window, date string, title string, a height integer and a font-size string (in the format "xxpt"). Generates an event box based on these modifiers. */
function addBox(w, date, title, titleH, datesS) {
    w.document.write(
        `<div class="event">
            <div class="date" style="font-size:${datesS}; color:${monthColor}">${date}</div>
            <div class="title">
                <span class="title-span" style="background-color:${monthColor}">${title}</span>
            </div>
        </div>`
    );
}

/* Receives a window and adds the HTML footer to it. */
function footer(w) {
    w.document.write("</div></div></div></body></html>");
}

function save(w) {
    html2canvas(w.document.getElementById("canvas-container")).then(function (canvas) {
        canvas.id = "canvas";
        canvas.style.display = "none";
        w.document.body.appendChild(canvas);
    }).then(function() {
        let canvas = w.document.getElementById("canvas");
        let img = canvas.toDataURL("image/png", 1.0);
        img.crossOrigin = "anonymous";
        let a = w.document.createElement('a');
        a.href = img;
        a.download = "calendario.png";
        a.innerHTML = '<button class="custom-button" style="width: 1200px">Salvar Calendário</button>'
        w.document.body.prepend(a);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    const downloadButton = document.getElementById("downloadCalendarBtn");
    downloadButton.addEventListener("click", (e) => {
        e.preventDefault();

        // Convert activitiesData to a Map-like object
        const dataMap = new Map();
        dataMap.set("month", month);

        activitiesData.forEach((activity, index) => {
            dataMap.set(`date_${index + 1}`, activity.date || activity.date);
            dataMap.set(`info_${index + 1}`, `${activity.title}<br><span class="time_text">${activity.hour_start || ""}</span>`);
        });

        // Call the downloadCalendar function with the simulated data
        downloadCalendar({
            preventDefault: () => {}, // Mock preventDefault
            target: dataMap,
        });
    });
});