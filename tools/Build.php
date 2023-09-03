<?php

declare(strict_types=1);

Build::init();
Build::id();
// echo Build::toc();


class Build
{
    static $dom;
    static $trans;
    static $init;
    static public function init()
    {
        self::$dom = new DOMDocument();
        self::$dom->substituteEntities = true;
        self::$dom->preserveWhiteSpace = true;
        self::$dom->formatOutput = false;
        self::$trans = new XSLTProcessor();
    }

    static public function id()
    {
        self::$dom->load(__DIR__ . '/cts_divid.xsl');
        self::$trans->importStyleSheet(self::$dom);
        self::scan(function($file){
            self::$dom->load($file->getPathname());
            self::$trans->transformToUri(self::$dom, $file->getPathname());
        });
    }


    static public function toc()
    {
        self::$dom->load(__DIR__ . '/galenus_toc.xsl');
        self::$trans->importStyleSheet(self::$dom);

        echo "<h1>Galenus Verbatim, tabula<h1>\n";
        self::scan(function($file){
            $pos = strlen(__DIR__);
            $path = str_replace('\\', '/', substr($file->getPathname(), $pos + 1)) ;
            self::$trans->setParameter("", "path", $path);
            self::$dom->load($file->getPathname());
            // echo $path . "\n";
            echo  self::$trans->transformToXml(self::$dom);
        });
    }
    public static function scan($callback)
    {
        $dir = dirname(__DIR__);
        $dst_url = "https://galenus-verbatim.github.io/galenus_cts/";
        $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir));
        $i = 1;
        foreach ($iterator as $file) {
            if ($file->isDir()) continue;
            $file_name = $file->getFileName();
            if (strpos($file_name ,'tlg') !== 0) continue;
            $callback($file, $i);
            $i++;
        }
    }

}
