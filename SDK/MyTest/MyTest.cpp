
#include <iostream>
#include "parse_metafile.h"

using namespace std;

int main()
{
    char *metafile="Vantage_Point.torrent";
    parse_metafile(metafile);

    system("pause");
    return 0;
}
