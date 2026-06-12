function isNumber(evt) {
    evt = evt ? evt : window.event;
    var charCode = evt.which ? evt.which : evt.keyCode;
    if (charCode > 31 && (charCode < 48 || charCode > 57)) {
        return false;
    }
    return true;
}

function hideButtonSalvar() {
    $(".salvar").hide();
    $(".loading").show();
}

function showButtonSalvar() {
    $(".salvar").show();
    $(".loading").hide();
}

function notifySuccess(text) {
    Toastify({
        text: text,
        duration: 3000,
        className: "success",
        newWindow: true,
        close: true,
        gravity: "top", // `top` or `bottom`
        position: "center", // `left`, `center` or `right`
        stopOnFocus: true, // Prevents dismissing of toast on hover
        style: {
            background: "linear-gradient(to right, #00b09b, #96c93d)",
        },
        onClick: function () {
        }, // Callback after click
    }).showToast();
}

function notifyError(text) {
    Toastify({
        text: text,
        duration: 3000,
        className: "error",
        newWindow: true,
        close: true,
        gravity: "top", // `top` or `bottom`
        position: "center", // `left`, `center` or `right`
        stopOnFocus: true, // Prevents dismissing of toast on hover
        style: {
            background: "linear-gradient(to right, #9b0505, #b76464)",
        },
        onClick: function () {
        }, // Callback after click
    }).showToast();
}

function pesquisacep(valor, callback) {
    return webServiceCep1(valor, callback);
}

function webServiceCep1(valor, callback) {
    //Nova variÃ¡vel "cep" somente com dÃ­gitos.
    var cep = valor.replace(/\D/g, "");

    //Verifica se campo cep possui valor informado.
    if (cep != "") {
        //ExpressÃ£o regular para validar o CEP.
        var validacep = /^[0-9]{8}$/;

        //Valida o formato do CEP.
        if (validacep.test(cep)) {
            //Preenche os campos com "..." enquanto consulta webservice.

            //Cria um elemento javascript.
            var script = document.createElement("script");

            //Sincroniza com o callback.
            script.src =
                "https://viacep.com.br/ws/" + cep + "/json/?callback=" + callback;

            //Insere script no documento e carrega o conteÃºdo.
            document.body.appendChild(script);
        } //end if.
        else {
            alert("Formato de CEP inválido.");
        }
    } //end if.
    else {
    }
}

function passwordCheck() {
    $(".error").hide();
    var hasError = false;
    var passwordVal = $("#usePassword").val();
    var checkVal = $("#password-input").val();
    $("#password-check").hide();
    if (passwordVal != checkVal) {
        $("#password-check").show();
    }
}

$("#termoLink").on("click", function (e) {
    e.preventDefault();
    $("#termoModal").modal("show");
});

function stripHtml(html) {
    let doc = new DOMParser().parseFromString(html, "text/html");
    return doc.body.textContent || "";
}

$("#topnav-hamburger-icon").on("click", function (e) {
    //const screenWidth = document.documentElement.clientWidth;
    let isMobile = false;

    // detecção de dispositivo
    if (
        /(android|bb\d+|meego).+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|ipad|iris|kindle|Android|Silk|lge |maemo|midp|mmp|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino/i.test(
            navigator.userAgent
        ) ||
        /1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i.test(
            navigator.userAgent.substr(0, 4)
        )
    ) {
        isMobile = true;
    }

    /*if (!isMobile) {
        if (sessionStorage.getItem("data-sidebar-size") == "lg") {
            //console.log('passei')
            document.documentElement.setAttribute("data-sidebar-size", "sm");
            document.querySelector(".ri-menu-fill").classList.add("open");
            sessionStorage.setItem("data-sidebar-size", "sm");
        } else {
            //console.log('passei2')
            document.documentElement.setAttribute("data-sidebar-size", "lg");
            document.querySelector(".ri-menu-fill").classList.remove("open");
            sessionStorage.setItem("data-sidebar-size", "lg");
        }
        setTimeout(function () {
            document.documentElement.setAttribute("data-sidebar-size", sessionStorage.getItem("data-sidebar-size"));
            //console.log(sessionStorage.getItem("data-sidebar-size"))
            if (sessionStorage.getItem("data-sidebar-size") == "sm") {
                document.querySelector(".ri-menu-fill").classList.add("open");
            } else {
                document.querySelector(".ri-menu-fill").classList.remove("open");
            }
        }, 50);
    } else {*/
        /*var navbarMenu = document.getElementById("navbar-menu");
        var header = document.querySelector("header");
        var btn = document.querySelector("#topnav-hamburger-icon");

        if (navbarMenu && header && btn) {
            var btnWidth = btn.offsetWidth;

            if (navbarMenu.classList.contains("active")) {
                header.style.transform = "translateX(0)";
            } else {
                header.style.transform = "translateX(" + btnWidth + "px)";
            }
            navbarMenu.classList.toggle("active");
        }*/
    /*}*/

    //console.log(sessionStorage.getItem("data-sidebar-size"));
});

function verificarECorrigirData(dataDigitada) {
    // Verificar se a data está no formato correto "dd/mm/aa" ou "dd/mm/aaaa"
    const regexData = /^(\d{2})\/(\d{2})\/(\d{2}|\d{4})$/;

    if (!regexData.test(dataDigitada)) {
        //return "Data incorreta. Utilize o formato dd/mm/aa ou dd/mm/aaaa.";
        return "";
    }

    const partes = dataDigitada.match(regexData);
    let dia = parseInt(partes[1]);
    let mes = parseInt(partes[2]);
    let ano = parseInt(partes[3]);

    // Verificar se o ano é bissexto (para fevereiro)
    const isBissexto = (ano % 4 === 0 && ano % 100 !== 0) || ano % 400 === 0;
    const maxDiasPorMes = [31, isBissexto ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

    // Corrigir o dia, mês e ano, se forem inválidos
    if (mes < 1 || mes > 12) {
        mes = Math.max(1, Math.min(12, mes));
    }
    if (dia < 1 || dia > maxDiasPorMes[mes - 1]) {
        dia = Math.max(1, Math.min(maxDiasPorMes[mes - 1], dia));
    }
    if (ano >= 0 && ano < 100) {
        // Converter o ano de dois dígitos para quatro dígitos
        const anoAtual = new Date().getFullYear();
        const seculo = Math.floor(anoAtual / 100) * 100; // Obter o século atual
        ano += seculo; // Adicionar o século ao ano de dois dígitos
    } else if (ano < 1900 || ano > 2099) {
        // Corrigir o ano dentro do intervalo desejado (1900-2099)
        ano = Math.max(1900, Math.min(2099, ano));
    }

    // Formatar a data corrigida
    const diaCorrigido = dia.toString().padStart(2, '0');
    const mesCorrigido = mes.toString().padStart(2, '0');
    const anoCorrigido = ano.toString();

    return `${diaCorrigido}/${mesCorrigido}/${anoCorrigido}`;
}

/*
$('input[name="addCep"]').api({
  beforeSend: function (settings) {
    settings.urlData = {
      cep: $(this).val(),
      format: "json",
    };
    return true;
  },
  url: "http://cep.republicavirtual.com.br/web_cep.php?cep={cep}&formato={format}",
  on: "change",
  method: "GET",
  stateContext: ".cepdep",
  onSuccess: function (response) {
    $(".form.ui").form("set values", {
      addCity: response.cidade,
      addNeighborhood: response.bairro,
      addState: response.uf,
      addStreet: response.tipo_logradouro + " " + response.logradouro,
    });
  },
});
*/
