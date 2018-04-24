<!DOCTYPE html>
<html>
  <head>
    <title>Music Tagger</title>
    <meta charset="UTF-8">
  </head>
  <body>
  <div id="tail">
  <?php
    $target_dir = "/var/www/html/uploads/";
    $filesUploaded = 0;
    $totalFiles = 0;
    if (isset($_FILES["filesToUpload"])){
      $totalFiles = count($_FILES["filesToUpload"]["name"]);
      echo "Removing existing files...";
      echo shell_exec('rm -f /var/www/html/uploads/* 2>&1');
    }
    for($i=0; $i<$totalFiles; $i++) {
      $target_file = $_FILES["filesToUpload"]["name"][$i];
      $uploadOk = 1;
      $target_file = $target_dir . preg_replace("/ /", "_", basename($target_file));
      $fileType = pathinfo($target_file,PATHINFO_EXTENSION);
      if(isset($_POST["submit"])) {
       if($_FILES["filesToUpload"]["type"][$i] == "audio/m4a" || $fileType == "m4a") {
            echo "File is an mp4. ";
        } else {
            echo "File is not an mp4. ";
            $uploadOk = 0;
        }
      }
      if ($_FILES["filesToUpload"]["size"][$i] > 20000000) {
        echo "Sorry, your file is too large.";
        $uploadOk = 0;
      }
      if ($uploadOk == 0) {
          echo "Sorry, your file was not uploaded.";
      } else {
        if (move_uploaded_file($_FILES["filesToUpload"]["tmp_name"][$i], $target_file)) {
            echo "The file ". basename( $_FILES["filesToUpload"]["name"][$i]). " has been uploaded. ";
            $filesUploaded = 1;
        } else {
            echo "Sorry, there was an error uploading your file. ";
        }
      }
      if ($filesUploaded) {
        $command = escapeshellcmd('/usr/bin/python3 /var/www/html/src/musicCorrectorWeb.py 2>&1');
        echo "Executing ".$command."...";
        exec($command,$output,$return);
        echo "<p>".$return."</p>";
        foreach ($output as $line){
          echo $line;
        }
      }
    }
  ?>
  </div>
  </body>
</html>
