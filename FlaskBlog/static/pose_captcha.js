function preview_snapshot() {
	$(".smalltext").html("GET READY IN");
	$("#clockdiv .seconds").html("");
	document.getElementById('pre_take_buttons').style.display = 'none';

	//Timer function 
	function timer_div() {
        // Set count down seconds
        var seconds = 3;

        // Update the count down every 1 second
        var x = setInterval(function() {
        	// Output the result in the element "#clockdiv .seconds"
            $("#clockdiv .seconds").html(seconds+ "s ");

            // If the count down is over, write some text 
            if (seconds <= 0) {
                clearInterval(x);
                 $(".smalltext").html("");
                 $("#clockdiv .seconds").html("POSE");
                 
                 setTimeout(function() { 
                 	// freeze camera so user can preview pic
                 	Webcam.freeze();
                 	$("#clockdiv .seconds").html("Save and Submit");
                 	// swap button sets
					document.getElementById('pre_take_buttons').style.display = 'none';
					document.getElementById('post_take_buttons').style.display = '';
					 }, 1000);                 
            }
            seconds = seconds - 1
        }, 1000);
    }			
	//Show Timer div
	$( "#clockdiv").show( "slow", timer_div());
	$( "#clockdiv" ).delay(10000).hide( "slow" );
}

function cancel_preview() {
	// cancel preview freeze and return to live camera feed
	Webcam.unfreeze();
	
	// swap buttons back
	document.getElementById('pre_take_buttons').style.display = '';
	document.getElementById('post_take_buttons').style.display = 'none';

}

function save_photo() {
	Webcam.snap( function(data_uri) {
		$("#submit_form").attr("disabled", true);
		$("#pose_captcha").fadeOut(500);
		$("#pose_captcha").html('<p>Pose Captcha being verified ...</p>\
									<hr>\
									<img src="{{ url_for('static', filename='loading.gif') }}" alt="Verified" class ="img-responsive"  width="400" height="400">');
		$("#pose_captcha").fadeIn(100);
		
		// snap complete, image data is in 'data_uri'
		Webcam.upload( data_uri, '/test', function(code, text) {
			// Upload complete!
			// 'code' will be the HTTP response code from the server, e.g. 200
			// 'text' will be the raw response content
			//alert("Inside Upload");
			var data = JSON.parse(text);
			if (data.human == "True") {
				$("#pose_verified").val(data.token);
				$("#pose_captcha").fadeOut(500);
				$("#pose_captcha").html('<p>Pose Captcha <b>Verified</b>.</p>\
									<hr>\
									<img src="{{ url_for('static', filename='checkmark.gif') }}" alt="Verified" class ="img-responsive"  width="400" height="400">');
				$("#pose_captcha").fadeIn(100);
				$("#pose_verified_error").hide("slow");
				Webcam.reset();
				$(":submit").removeAttr("disabled");
			}
			else{
				$("#pose_verified").val("False");
				$("#pose_captcha").fadeOut(500);
				$("#pose_captcha").html('<p>You have <b>failed</b> Pose Captcha, refresh and try again.</p>\
								<hr>\
								<img src="{{ url_for('static', filename='nothuman.gif') }}" alt="Not Verified" class ="img-responsive">');
				$("#pose_captcha").fadeIn(100);
				Webcam.reset();
				$("#submit_form").removeAttr("disabled");
			}				
		} );				
	} );
}