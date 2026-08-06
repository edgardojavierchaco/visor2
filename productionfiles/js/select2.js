$(document).ready(function () {

    $(".select2-ajax").select2({
        ajax: {
            url: "/ajax/select2/",
            dataType: "json",
            delay: 250,
            data: function (params) {
                return {
                    q: params.term,
                    model: $(this).data("model")
                };
            },
            processResults: function (data) {
                return {
                    results: data.results.map(function (item) {
                        const key = Object.keys(item)[1];
                        return {
                            id: item.id,
                            text: item[key]
                        };
                    })
                };
            }
        },
        minimumInputLength: 2,
        width: "100%"
    });

});