/* 
GLOBAL VARIABLES
*/

let dates = [];
let titles = [];
let titlesH = [];
let datesS = [];
let w;
let total_boxes = 0;
let month;
let monthColor;

/*
GLOBAL CONSTANTS -- CSS MODIFIERS

If these values are edited in calendar.css, they must also be manually
edited here. All of them are in pixels.

max_height     height value of 'evento' css class
box_margin     margin-top value of 'evento' css class
total_height   height value of 'container' css id
lineHeight     line-height value of 'titulo' css class
*/

const max_height = 1080;
const box_margin = 20;
const total_height = 1200;
const lineHeight = 37;


/*
  Prevents the form entries from being erased upon submission.
  Generates a new window with the calendar image version of the
  form input.
*/
function processForm(e) {
    if (e.preventDefault) e.preventDefault();
    const formData = new FormData(e.target);
    w = window.open();
    resetVariables();
    getFormData(formData);
    getMonthValues();
    addHTML(w);
    save(w);

    return false;
}

/*
  Attaches the form processing function to the form
*/

var form = document.getElementById("submitForm");
if (form.attachEvent) {
    form.attachEvent("submit", processForm);
} else {
    form.addEventListener("submit", processForm);
}


/*
  Save image function -- currently not working
*/

function save(w) {
    html2canvas(w.document.getElementById("container")).then(function (canvas) {
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
        a.innerHTML = "<button type=\"button\" style=\"width: 1200px\">Salvar Calendário</button>"
        w.document.body.prepend(a);
    });
}

/* 
  Switches the font color based on the month. 
  Should be edited to also switch the background image.
*/

function getMonthValues() {
    switch (month) {
        case "janeiro":
            monthColor = "#000000";
            break;
        case "fevereiro":
            monthColor = "#5f174a";
            break;
        case "março":
            monthColor = "#242856";
            break;
        case "abril":
            monthColor = "#2c70b7";
            break;
        case "maio":
            monthColor = "#23772d";
            break;
        case "junho":
            monthColor = "#e6520f";
            break;
        case "julho":
            monthColor = "#c10248";
            break;
        case "agosto":
            monthColor = "#016668";
            break;
        case "setembro":
            monthColor = "#f9b215";
            break;
        case "outubro":
            monthColor = "#d81d61";
            break;
        case "novembro":
            monthColor = "#18499a";
            break;
        case "dezembro":
            monthColor = "#cc1517";
            break;
    }
}

/*
  Resets the values of the arrays upon each submission
  of the form.
*/
function resetVariables() {
    dates = [];
    titles = [];
    titlesH = [];
    datesS = [];
    monthColor = "";
}

/*
  Receives a formData object. Extracts the date, title and month
  fields from the form, and saves them to their respective
  global variables.
*/
function getFormData(formData) {
    dates = [];
    titles = [];
    let i = 1;
    let info;
    for (let i = 1; i < 11; i++) {
        // gets dates
        if (formData.get("date" + i) != "") {
            info = formData.get("date" + i);
            info = info.replace(/\r?\n/g, '<br>');
            dates.push(info)
        }
        // gets event titles
        if (formData.get("line" + i) != "") {
            info = formData.get("line" + i);
            info = info.replace(/\r?\n/g, '<br>');
            titles.push(info)
        }
    }
    total_boxes = dates.length;

    // gets the form's month
    month = formData.get("month");
}

/*
  Receives a window and generates the HTML to it.
*/
function addHTML(w) {
    try {
        header(w);
        calculateDateFontSize(w);
        calculateHeights(w);
        addBoxes(w);
        footer(w);
    } catch {
        w.document.write("<div class='evento' style='color:white; size:30px'>Algo deu errado. (Provavelmente você preencheu um campo de data de um evento e deixou o título do mesmo em branco.)</div>");
    }
}


/*
  Calculates the font size of the date field.
  There might be some issues here depending on the
  form the date input.
*/
function calculateDateFontSize(w) {
    for (let i = 0; i < total_boxes; i++) {
        if (dates[i].length < 5) {
            datesS[i] = "33pt";

        }
        // strings such as "TODO SÁBADO", "14, 21 e 28"
        else {
            datesS[i] = "22pt";
        }
    }
}

/*
  Receives a window and adds the html header to it.
*/
function header(w) {
    w.document.write("<html>\
    <head>\
    <title>Calendário</title>\
    </head>\
    <body style='padding: 0;margin: 0'>\
    <div class='w3-container'>\
    <div id='container' style='background-image:url(" + "\"static/images/" + month + ".png\");background-size: 1200px'>" +
        "<div id='calendar-main'>");

    var head = w.document.getElementsByTagName('HEAD')[0];
    var link = w.document.createElement('link');
    link.rel = 'stylesheet';
    link.type = 'text/css';
    link.href = 'static/style.css';
    head.appendChild(link);
}

/*
  Receives a window (for debugging purposes). Calculates the 
  height each event div should have based on the number of lines 
  it's respective title field has. The global variable lineHeight
  can be used to determine when an event must be resized.
*/
function calculateHeights(w) {
    let sameHeight = (max_height - (total_boxes - 1) * box_margin) / (total_boxes);
    let resized = 0;

    for (let i = 0; i < total_boxes; i++) {
        if (lineHeight * titles[i].match(/<br>/g).length > sameHeight) {
            titlesH[i] = lineHeight * titles[i].match(/<br>/g).length;
            resized += 1;
        } else {
            titlesH[i] = 0;
        }
    }
    if (resized) {
        let leftoverHeight = max_height - titlesH.reduce(function (pv, cv) {
            return pv + cv;
        }, 0);
        sameHeight = (leftoverHeight - (total_boxes - 1) * box_margin) / (total_boxes - resized);
    }

    for (let i = 0; i < total_boxes; i++) {
        if (titlesH[i] == 0) titlesH[i] = sameHeight;
    }
}

/*
  Receives a window and adds each event div to it, along with 
  it's respective titlesH (titles height) and datesS (date font-size)
  style modifiers.
*/
function addBoxes(w) {
    for (let i = 0; i < total_boxes; i++) {
        addBox(w, dates[i], titles[i], titlesH[i], datesS[i]);
    }
}

/*
  Receives a window, date string, title string, a height integer and 
  a font-size string (in the format "xxpt"). Generates an event box based
  on these modifiers.
*/
function addBox(w, date, title, titleH, datesS) {
    w.document.write('<div class = "evento" style="height:', titleH, 'px">\
    <div class = "data" style="font-size:', datesS, '; color:', monthColor, '">', date,
        '</div>\
        <div class = "titulo"><div>\
        <span class ="titulo-span" style="background-color:', monthColor, '">', title, '</span><br>\
    </div></div>\
    </div>');
}

/*
  Receives a window and adds the HTML footer to it.
*/
function footer(w) {
    w.document.write("</div>\
    </div>\
    </div>\
  </body>\
</html>");
}


/*
  Converts the filled form values to a string the format:
  Date;Event title
*/

function exportForm() {
    let string = "";
    document.getElementById("export").value = "";
    var formData_aux = new FormData(document.forms.submitForm);
    var formData = getFormData(formData_aux);
    for (let i = 0; i < total_boxes; i++) {
        string += dates[i] + ";" + titles[i] + "\n";
    }
    total_boxes=0;
    document.getElementById("export").value = string.replace(/\n$/, '');;
}

/*
  Receives a previous exported calendar string and 
  uses it to auto-fill the form fields.
*/

function importForm() {
    let lines = document.getElementById("import").value.split("\n");
    if (validateImport(lines)) {
        let formDates = document.getElementsByClassName("date");
        let formTitles = document.getElementsByClassName("field");
        for (let i = 0; i < lines.length; i++) {
            let value = lines[i].split(";");
            if (value.length != 2) break;
            formDates[i].value = value[0].replace(/<br>/g, "\n");
            formTitles[i].value = value[1].replace(/<br>/g, "\n");
        }
    } else {
        window.alert("Algo está errado com o texto que você tentou importar.");
    }


}

/*
  Checks if theres something wrong with the string input.
*/
function validateImport(lines) {
    let split;
    for (let i = 0; i < lines.length; i++) {
        split = lines[i].split(";");
        if (split[0] != "" && split.length != 2) return false;
    }
    return true;
}
