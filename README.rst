Summary
=======

Lazythumbs acts as a `PIL <http://www.pythonware.com/products/pil/>`_ proxy
for images stored in MEDIA_ROOT. It looks for the requested image and, if
found, generates a new image and writes it to the filesystem at
MEDIA_ROOT/lt_cache.  If the request resulted in a 404, the 404 response is
cached to avoid getting hammered by repeated requests for images that don't
exist.

Lazythumbs can be utilized from within a Django project's templates, or
from without through the image request API. Images are produced and cached
from their sources on-demand.

Online documentation:
`http://docs.cmgdigital.com/lazythumbs.git/ <http://docs.cmgdigital.com/lazythumbs.git/>`_.

Meta
----

lazythumbs is in many ways a combination of `sorl-thumbnail <https://github.com/sorl/sorl-thumbnail>`_
and `thumpy <http://bits.btubbs.com/thumpy>`_ and owes its existence to them both.

lazythumbs was written by nathaniel k smith <nathanielksmith@gmail.com> for
`cmg digital&strategy <http://cmgdigital.com/>`_ and is licensed under the terms of the
MIT license.
