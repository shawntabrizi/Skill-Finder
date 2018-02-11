/**
 * Created by aclawson on 7/25/17.
 */
$(document).ready(function() {
    var els1 = $('#confirmed').children().children('.item').toArray();
    var confirmed = els1.map(function(el){return el.textContent});
    var els2 = $('#other').children().children('.item').toArray();
    var suggestions = els2.map(function(el){return el.textContent});
    var pub_choices = {
        'clipboard': false,
        'linkedIn': false,
        'delve': false,
        'drWho': false
    }

    console.log("Confirmed:", confirmed, "Other:", suggestions);

    /* Toggling between items that are confirmed and suggested */
    $('#confirmed').on('click', '.list-confirmed', function(){
        var text = $(this).children('.item').text();
        var idx = confirmed.indexOf(text);
        confirmed.splice(idx, 1);
        suggestions.push(text);
        $(this).detach();
        $('#other').append($(this));
        $(this).find('bold').text("+");
        $(this).removeClass("list-confirmed").addClass("list-other");
        console.log("Removed from confirmed:", text, confirmed)
    });

    $('#other').on('click', '.list-other', function(){
        var text = $(this).children('.item').text();
        var idx = suggestions.indexOf(text);
        suggestions.splice(idx, 1);
        confirmed.push(text);
        $(this).detach()
        $('#confirmed').append($(this));
        $(this).find('bold').text("x");
        $(this).removeClass("list-other").addClass("list-confirmed");
        console.log("Removed from suggestions:", text, suggestions)
    });

    /* Toggle the publish targets */
    $('.publish').on('click', '.pub', function(){
        $(this).toggleClass('orange-solid');
        var id = $(this).attr('id');
        pub_choices[id] = !pub_choices[id];
    })

    $('.publish').on('click', '#publish', function(){
        var payload = {
            pubChoices: pub_choices,
            confirmed: confirmed,
            other: suggestions
        }
        $.ajax({
            url: '/skills',
            type: "POST",
            data: JSON.stringify(payload, null, '\t'),
            contentType: "application/json;charset=utf-8",
            success: function(){
                $('.publish').append("<h4>Success</h4>")
                window.prompt("Copy to clipboard: Ctrl+C / Cmd+C, Enter", confirmed);
            },
            error: function(){
                $('.publish').append("<h4>An error occurred</h4>")
            }
        })
    })

})