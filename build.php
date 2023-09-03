<?php

declare(strict_types=1);
echo Read::scan();


class Read
{
    public static function scan($dir = __DIR__)
    {
        $dst_url = "https://galenus-verbatim.github.io/galenus_cts/";
        $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir));
        $out = [];
        $out[] = "| N° | CTS     |";
        $out[] = "| -: | ------: |";

        $i = 1;
        foreach ($iterator as $file) {
            if ($file->isDir()) continue;
            $file_name = $file->getFileName();
            if (strpos($file_name ,'tlg') !== 0) continue;

            $cts = "urn:cts:greekLit:" . pathinfo($file_name, PATHINFO_FILENAME);
            $pos = strlen(__DIR__);
            $path = str_replace('\\', '/', substr($file->getPathname(), $pos + 1)) ;

            $out[] = "|$i." 
            . "|" . "[$cts]($dst_url$path)" 
            . "|";
            $i++;
        }
        return implode("\n", $out);
    }

}
