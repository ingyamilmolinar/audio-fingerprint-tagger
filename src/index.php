<!DOCTYPE html>
<html>
	<head>
		<title>Music Tagger</title>
		<meta charset="UTF-8">
	</head>

	<body>
		<form action="src/upload.php" method="post" enctype="multipart/form-data">
    		Select files to upload:<br>
    		<input type="file" name="filesToUpload[]" multiple="multiple"/><br>
    		<input type="submit" value="Upload Files" name="submit"/>
		</form>
	</body>
</html> 
