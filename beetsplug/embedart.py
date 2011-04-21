import logging
import imghdr

from beets.plugins import BeetsPlugin
from beets import mediafile
from beets import ui
from beets.util import syspath, normpath

log = logging.getLogger('beets')

def _embed(path, items):
    """Embed an image file, located at `path`, into each item.
    """
    data = open(syspath(path), 'rb').read()
    kindstr = imghdr.what(None, data)

    if kindstr == 'jpeg':
        kind = mediafile.imagekind.JPEG
    elif kindstr == 'png':
        kind = mediafile.imagekind.PNG
    else:
        log.error('A file of type %s is not allowed as coverart.' % kindstr)
        return

    # Add art to each file.
    log.debug('Embedding album art.')
    for item in items:
        f = mediafile.MediaFile(syspath(item.path))
        f.art = (data, kind)
        f.save()

options = {
    'autoembed': True,
}
class EmbedCoverArtPlugin(BeetsPlugin):
    """Allows albumart to be embedded into the actual files."""
    def configure(self, config):
        options['autoembed'] = \
            ui.config_val(config, 'embedart', 'autoembed', True, bool)

    def commands(self):
        # Embed command.
        embed_cmd = ui.Subcommand('embedart',
                                  help='embed an image file into file metadata')
        def embed_func(lib, config, opts, args):
            if not args:
                raise ui.UserError('specify an image file')
            imagepath = normpath(args.pop(0))
            embed(lib, imagepath, ui.make_query(args))
        embed_cmd.func = embed_func

        # Extract command.
        extract_cmd = ui.Subcommand('extractart',
                                    help='extract an image from file metadata')
        extract_cmd.parser.add_option('-o', dest='outpath',
                                      help='image output file')
        def extract_func(lib, config, opts, args):
            outpath = normpath(opts.outpath or 'cover')
            extract(lib, outpath, ui.make_query(args))
        extract_cmd.func = extract_func

        return [embed_cmd, extract_cmd]

# "embedart" command.
def embed(lib, imagepath, query):
    albums = lib.albums(query=query)
    for i_album in albums:
        album = i_album
        break
    else:
        log.error('No album matches query.')
        return

    log.info('Embedding album art into %s - %s.' % \
             (album.albumartist, album.album))
    _embed(imagepath, album.items())

# "extractart" command.
def extract(lib, outpath, query):
    items = lib.items(query=query)
    for i_item in items:
        item = i_item
        break
    else:
        log.error('No item matches query.')
        return

    # Extract the art.
    print syspath(item.path)
    mf = mediafile.MediaFile(syspath(item.path))
    art = mf.art
    if not art:
        log.error('No album art present in %s - %s.' %
                  (item.artist, item.title))
        return
    data, kind = art

    # Add an extension to the filename.
    if kind == mediafile.imagekind.JPEG:
        outpath += '.jpg'
    else:
        outpath += '.png'

    log.info('Extracting album art from: %s - %s\n'
             'To: %s' % \
             (item.artist, item.title, outpath))
    with open(syspath(outpath), 'wb') as f:
        f.write(data)

# Automatically embed art into imported albums.
@EmbedCoverArtPlugin.listen('album_imported')
def album_imported(lib, album):
    if album.artpath and options['autoembed']:
        _embed(album.artpath, album.items())
