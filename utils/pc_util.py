""" Utility functions for processing point clouds.

Author: Charles R. Qi, Hao Su
Date: November 2016
"""

import os
import sys
import math
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Draw point cloud
from eulerangles import euler2mat

# Point cloud IO
import numpy as np
from plyfile import PlyData, PlyElement
import pymesh
import open3d
from tqdm import tqdm

##################### colors for vis #############################
picked_colors = [[103, 103, 130],
                [44, 44, 160],
                [149, 149, 249],
                [196, 196, 219],
                [52, 52, 61],
                [139, 139, 81],
                [239, 239, 50],
                [231, 231, 189],
]
# from scannet
'''
other_colors = [
    'unannoated': [0, 0, 0],
    'desk': [247,183,210],
    'bookshelf': [148,103,188], 
    'sink': [112,128,144], 
    'bathtub': [227,119,194], 
    'toilet': [43,160,45], 
    'curtain': [218,219,141], 
    'counter': [23,190,208], 
    'shower curtain': [158,218,229], 
    'refridgerator': [254,127,14], 
    'picture': [196,156,148], 
    'cabinet': [31,120,180], 
    'otherfurniture': [82,83,163]
]
'''
color_dict = {
    'unannotated': [0, 0, 0], 
    'wall': picked_colors[0], 
    'floor': picked_colors[1], 
    'chair': picked_colors[2], 
    'table': picked_colors[3], 
    'desk': [247,183,210], 
    'bed': picked_colors[4], 
    'bookshelf': [148,103,188], 
    'sofa': picked_colors[7], 
    'sink': [112,128,144], 
    'bathtub': [227,119,194], 
    'toilet': [43,160,45], 
    'curtain': [218,219,141], 
    'counter': [23,190,208], 
    'door': picked_colors[5], 
    'window': picked_colors[6], 
    'shower curtain': [158,218,229], 
    'refridgerator': [254,127,14], 
    'picture': [196,156,148], 
    'cabinet': [31,120,180], 
    'otherfurniture': [82,83,163]
}
color_array = np.array([
    [0, 0, 0], 
    picked_colors[0], 
    picked_colors[1], 
    picked_colors[2], 
    picked_colors[3], 
    [247,183,210], 
    picked_colors[4], 
    [148,103,188], 
    picked_colors[7], 
    [112,128,144], 
    [227,119,194], 
    [43,160,45], 
    [218,219,141], 
    [23,190,208], 
    picked_colors[5], 
    picked_colors[6], 
    [158,218,229], 
    [254,127,14], 
    [196,156,148], 
    [31,120,180], 
    [82,83,163]
])

def get_color_by_name(cls_name):
    if cls_name not in color_dict.keys():
        print('Unkown class name!' + cls_name)
        return [0, 0, 0]
    return color_dict[cls_name]

def get_color_by_label(label_id):
    if label_id not in range(0, len(color_array)):
        print('Label id out of range!' + str(label_id))
        return [0,0,0]
    return color_array[label_id]

def get_color_by_label_array(label_arr):
    label_arr[label_arr<0] = 0
    return color_array[label_arr]

#####################################################################

 
# ----------------------------------------
# Point Cloud/Volume Conversions
# ----------------------------------------
def point_cloud_label_to_surface_voxel_label(point_cloud, label, res=0.0484):
    coordmax = np.max(point_cloud,axis=0)
    coordmin = np.min(point_cloud,axis=0)
    nvox = np.ceil((coordmax-coordmin)/res)
    vidx = np.ceil((point_cloud-coordmin)/res)
    vidx = vidx[:,0]+vidx[:,1]*nvox[0]+vidx[:,2]*nvox[0]*nvox[1]
    uvidx = np.unique(vidx)
    if label.ndim==1:
        uvlabel = [np.argmax(np.bincount(label[vidx==uv].astype(np.uint32))) for uv in uvidx]
    else:
        assert(label.ndim==2)
    uvlabel = np.zeros(len(uvidx),label.shape[1])
    for i in range(label.shape[1]):
	    uvlabel[:,i] = np.array([np.argmax(np.bincount(label[vidx==uv,i].astype(np.uint32))) for uv in uvidx])
    return uvidx, uvlabel, nvox

def point_cloud_label_to_surface_voxel_label_fast(point_cloud, label, res=0.0484):
    coordmax = np.max(point_cloud,axis=0)
    coordmin = np.min(point_cloud,axis=0)
    nvox = np.ceil((coordmax-coordmin)/res)
    vidx = np.ceil((point_cloud-coordmin)/res)
    vidx = vidx[:,0]+vidx[:,1]*nvox[0]+vidx[:,2]*nvox[0]*nvox[1]
    uvidx, vpidx = np.unique(vidx,return_index=True)
    if label.ndim==1:
        uvlabel = label[vpidx]
    else:
        assert(label.ndim==2)
    uvlabel = label[vpidx,:]
    return uvidx, uvlabel, nvox

def point_cloud_to_volume_batch(point_clouds, vsize=12, radius=1.0, flatten=True):
    """ Input is BxNx3 batch of point cloud
        Output is Bx(vsize^3)
    """
    vol_list = []
    for b in range(point_clouds.shape[0]):
        vol = point_cloud_to_volume(np.squeeze(point_clouds[b,:,:]), vsize, radius)
        if flatten:
            vol_list.append(vol.flatten())
        else:
            vol_list.append(np.expand_dims(np.expand_dims(vol, -1), 0))
    if flatten:
        return np.vstack(vol_list)
    else:
        return np.concatenate(vol_list, 0)


def point_cloud_to_volume(points, vsize, radius=1.0):
    """ input is Nx3 points.
        output is vsize*vsize*vsize
        assumes points are in range [-radius, radius]
    """
    vol = np.zeros((vsize,vsize,vsize))
    voxel = 2*radius/float(vsize)
    locations = (points + radius)/voxel
    locations = locations.astype(int)
    vol[locations[:,0],locations[:,1],locations[:,2]] = 1.0
    return vol

#a = np.zeros((16,1024,3))
#print point_cloud_to_volume_batch(a, 12, 1.0, False).shape

def volume_to_point_cloud(vol):
    """ vol is occupancy grid (value = 0 or 1) of size vsize*vsize*vsize
        return Nx3 numpy array.
    """
    vsize = vol.shape[0]
    assert(vol.shape[1] == vsize and vol.shape[1] == vsize)
    points = []
    for a in range(vsize):
        for b in range(vsize):
            for c in range(vsize):
                if vol[a,b,c] == 1:
                    points.append(np.array([a,b,c]))
    if len(points) == 0:
        return np.zeros((0,3))
    points = np.vstack(points)
    return points

def point_cloud_to_volume_v2_batch(point_clouds, vsize=12, radius=1.0, num_sample=128):
    """ Input is BxNx3 a batch of point cloud
        Output is BxVxVxVxnum_samplex3
        Added on Feb 19
    """
    vol_list = []
    for b in range(point_clouds.shape[0]):
        vol = point_cloud_to_volume_v2(point_clouds[b,:,:], vsize, radius, num_sample)
        vol_list.append(np.expand_dims(vol, 0))
    return np.concatenate(vol_list, 0)

def point_cloud_to_volume_v2(points, vsize, radius=1.0, num_sample=128):
    """ input is Nx3 points
        output is vsize*vsize*vsize*num_sample*3
        assumes points are in range [-radius, radius]
        samples num_sample points in each voxel, if there are less than
        num_sample points, replicate the points
        Added on Feb 19
    """
    vol = np.zeros((vsize,vsize,vsize,num_sample,3))
    voxel = 2*radius/float(vsize)
    locations = (points + radius)/voxel
    locations = locations.astype(int)
    loc2pc = {}
    for n in range(points.shape[0]):
        loc = tuple(locations[n,:])
        if loc not in loc2pc:
            loc2pc[loc] = []
        loc2pc[loc].append(points[n,:])
    #print loc2pc

    for i in range(vsize):
        for j in range(vsize):
            for k in range(vsize):
                if (i,j,k) not in loc2pc:
                    vol[i,j,k,:,:] = np.zeros((num_sample,3))
                else:
                    pc = loc2pc[(i,j,k)] # a list of (3,) arrays
                    pc = np.vstack(pc) # kx3
                    # Sample/pad to num_sample points
                    if pc.shape[0]>num_sample:
                        choices = np.random.choice(pc.shape[0], num_sample, replace=False)
                        pc = pc[choices,:]
                    elif pc.shape[0]<num_sample:
                        pc = np.lib.pad(pc, ((0,num_sample-pc.shape[0]),(0,0)), 'edge')
                    # Normalize
                    pc_center = (np.array([i,j,k])+0.5)*voxel - radius
                    #print 'pc center: ', pc_center
                    pc = (pc - pc_center) / voxel # shift and scale
                    vol[i,j,k,:,:] = pc 
                #print (i,j,k), vol[i,j,k,:,:]
    return vol

def point_cloud_to_image_batch(point_clouds, imgsize, radius=1.0, num_sample=128):
    """ Input is BxNx3 a batch of point cloud
        Output is BxIxIxnum_samplex3
        Added on Feb 19
    """
    img_list = []
    for b in range(point_clouds.shape[0]):
        img = point_cloud_to_image(point_clouds[b,:,:], imgsize, radius, num_sample)
        img_list.append(np.expand_dims(img, 0))
    return np.concatenate(img_list, 0)


def point_cloud_to_image(points, imgsize, radius=1.0, num_sample=128):
    """ input is Nx3 points
        output is imgsize*imgsize*num_sample*3
        assumes points are in range [-radius, radius]
        samples num_sample points in each pixel, if there are less than
        num_sample points, replicate the points
        Added on Feb 19
    """
    img = np.zeros((imgsize, imgsize, num_sample, 3))
    pixel = 2*radius/float(imgsize)
    locations = (points[:,0:2] + radius)/pixel # Nx2
    locations = locations.astype(int)
    loc2pc = {}
    for n in range(points.shape[0]):
        loc = tuple(locations[n,:])
        if loc not in loc2pc:
            loc2pc[loc] = []
        loc2pc[loc].append(points[n,:])
    for i in range(imgsize):
        for j in range(imgsize):
            if (i,j) not in loc2pc:
                img[i,j,:,:] = np.zeros((num_sample,3))
            else:
                pc = loc2pc[(i,j)]
                pc = np.vstack(pc)
                if pc.shape[0]>num_sample:
                    choices = np.random.choice(pc.shape[0], num_sample, replace=False)
                    pc = pc[choices,:]
                elif pc.shape[0]<num_sample:
                    pc = np.lib.pad(pc, ((0,num_sample-pc.shape[0]),(0,0)), 'edge')
                pc_center = (np.array([i,j])+0.5)*pixel - radius
                pc[:,0:2] = (pc[:,0:2] - pc_center)/pixel
                img[i,j,:,:] = pc
    return img
# ----------------------------------------
# Point cloud IO
# ----------------------------------------

def read_ply(filename):
    """ read XYZ point cloud from filename PLY file """
    mesh = pymesh.load_mesh(filename)
    return mesh.vertices

def read_ply_xyz(filename):
    """ read XYZ point cloud from filename PLY file """
    if not os.path.isfile(filename):
        print(filename)
        assert(os.path.isfile(filename))
    with open(filename, 'rb') as f:
        plydata = PlyData.read(f)
        num_verts = plydata['vertex'].count
        vertices = np.zeros(shape=[num_verts, 3], dtype=np.float32)
        vertices[:,0] = plydata['vertex'].data['x']
        vertices[:,1] = plydata['vertex'].data['y']
        vertices[:,2] = plydata['vertex'].data['z']
    return vertices

def read_ply_xyzrgb(filename):
    """ read XYZRGB point cloud from filename PLY file """
    assert(os.path.isfile(filename))
    with open(filename, 'rb') as f:
        plydata = PlyData.read(f)
        num_verts = plydata['vertex'].count
        vertices = np.zeros(shape=[num_verts, 6], dtype=np.float32)
        vertices[:,0] = plydata['vertex'].data['x']
        vertices[:,1] = plydata['vertex'].data['y']
        vertices[:,2] = plydata['vertex'].data['z']
        vertices[:,3] = plydata['vertex'].data['red']
        vertices[:,4] = plydata['vertex'].data['green']
        vertices[:,5] = plydata['vertex'].data['blue']
    return vertices

def read_obj(filename):
    mesh = pymesh.load_mesh(filename)
    return mesh.vertices

def read_pcd(filename):
    pcd_load = open3d.read_point_cloud(filename)
    xyz_load = np.asarray(pcd_load.points)
    return xyz_load

def read_all_ply_under_dir(dir):
    '''
    return a list of arrays
    '''
    all_filenames = os.listdir(dir)
    ply_filenames = []
    for f in all_filenames:
        if f.endswith('.ply'):
            ply_filenames.append(os.path.join(dir, f))
    ply_filenames.sort()
    
    point_clouds = []
    for ply_f in tqdm(ply_filenames):
        pc = read_ply_xyz(ply_f)
        point_clouds.append(pc)
    
    return point_clouds

def read_ply_from_file_list(file_list):
    '''
    return a list of numpy array
    '''
    point_clouds = []
    for ply_f in tqdm(file_list):
        if not os.path.isfile(ply_f):
            print('Warning: skipping. ', ply_f)
            continue
        pc = read_ply_xyz(ply_f)
        point_clouds.append(pc)
    
    return point_clouds

def write_ply(points, filename, text=False):
    """ input: Nx3, write points to filename as PLY format. """
    points = [(points[i,0], points[i,1], points[i,2]) for i in range(points.shape[0])]
    vertex = np.array(points, dtype=[('x', 'f4'), ('y', 'f4'),('z', 'f4')])
    el = PlyElement.describe(vertex, 'vertex', comments=['vertices'])
    with open(filename, mode='wb') as f:
        PlyData([el], text=text).write(f)

def write_obj_color(points, labels, out_filename, num_classes=None):
    """ Color (N,3) points with labels (N) within range 0 ~ num_classes-1 as OBJ file """
    import matplotlib.pyplot as pyplot
    labels = labels.astype(int)
    N = points.shape[0]
    if num_classes is None:
        num_classes = np.max(labels)+1
    else:
        assert(num_classes>np.max(labels))
    fout = open(out_filename, 'w')
    colors = [pyplot.cm.hsv(i/float(num_classes)) for i in range(num_classes)]
    for i in range(N):
        c = colors[labels[i]]
        c = [int(x*255) for x in c]
        fout.write('v %f %f %f %d %d %d\n' % (points[i,0],points[i,1],points[i,2],c[0],c[1],c[2]))
    fout.close()

def write_obj_rgb(points, colors, out_filename, num_classes=None):
    """ Color (N,3) points with RGB colors (N,3) within range [0,255] as OBJ file """
    colors = colors.astype(int)
    N = points.shape[0]
    fout = open(out_filename, 'w')
    for i in range(N):
        c = colors[i,:]
        fout.write('v %f %f %f %d %d %d\n' % (points[i,0],points[i,1],points[i,2],c[0],c[1],c[2]))
    fout.close()

def write_pc_rgb_asXYZRGB(points, colors, out_filename, num_classes=None):
    """ Color (N,3) points with RGB colors (N,3) within range [0,255] as XYZRGB file """
    colors = colors / 255.
    N = points.shape[0]
    fout = open(out_filename, 'w')
    for i in range(N):
        c = colors[i,:]
        fout.write('%f %f %f %f %f %f\n' % (points[i,0],points[i,1],points[i,2],c[0],c[1],c[2]))
    fout.close()

def write_ply_batch(point_cloud_batch, out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    
    for pidx, pc in enumerate(point_cloud_batch):
        pc_name = os.path.join(out_dir, '%d.ply'%(pidx))
        write_ply(pc, pc_name)

def write_ply_batch_with_name(point_cloud_batch, name_batch, out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    
    for pidx, pc in enumerate(point_cloud_batch):
        pc_name = os.path.join(out_dir, name_batch[pidx])
        write_ply(pc, pc_name)

def write_ply_versatile(points, filename, colors=None, normals=None, text=False):
    """ input: Nx3, write points to filename as PLY format. """
    if colors is not None: assert(points.shape[0]==colors.shape[0])
    if normals is not None: assert(points.shape[0]==normals.shape[0])

    if colors is None and normals is None:
        points = [(points[i,0], points[i,1], points[i,2]) for i in range(points.shape[0])]
        vertex = np.array(points, dtype=[('x', 'f4'), ('y', 'f4'),('z', 'f4')])
    elif colors is not None and normals is None:
        points = [(points[i,0], points[i,1], points[i,2], 
                   int(colors[i, 0]*255), int(colors[i, 1]*255), int(colors[i, 2]*255)
                  ) for i in range(points.shape[0])]
        vertex = np.array(points, dtype=[('x', 'f4'), ('y', 'f4'), ('z', 'f4'), 
                                         ('red', 'u1'), ('green', 'u1'), ('blue', 'u1')])
    elif colors is None and normals is not None:
        points = [(points[i,0], points[i,1], points[i,2], 
                   normals[i, 0], normals[i, 1], normals[i, 2]
                  ) for i in range(points.shape[0])]
        vertex = np.array(points, dtype=[('x', 'f4'), ('y', 'f4'), ('z', 'f4'), 
                                         ('nx', 'f4'), ('ny', 'f4'), ('nz', 'f4')])
    elif colors is not None and normals is not None:
        points = [(points[i,0], points[i,1], points[i,2], 
                   normals[i, 0], normals[i, 1], normals[i, 2], 
                   int(colors[i, 0]*255), int(colors[i, 1]*255), int(colors[i, 2]*255)
                   ) for i in range(points.shape[0])]
        vertex = np.array(points, dtype=[('x', 'f4'), ('y', 'f4'), ('z', 'f4'), 
                                         ('nx', 'f4'), ('ny', 'f4'), ('nz', 'f4'), 
                                         ('red', 'u1'), ('green', 'u1'), ('blue', 'u1')])
    el = PlyElement.describe(vertex, 'vertex', comments=['vertices'])
    PlyData([el], text=text).write(filename)

# ----------------------------------------
# Point Cloud Manipulation
# ----------------------------------------
def point_cloud_center2ori(points):
    '''
    input:
        points: Nx3
    move the center of point cloud to the origin
    '''
    center = np.mean(points, axis=0)
    points = points - center
    return points
def point_cloud_bottom_center2ori(points):
    '''
    input: points - Nx3
    '''
    pts_min = np.amin(points, axis=0, keepdims=True)
    pts_max = np.amax(points, axis=0, keepdims=True)
    bbox_center = (pts_min + pts_max) / 2.0
    bbox_center[:,1] = 0

    res_pts = points - bbox_center

    return res_pts

def point_bbox(point_clouds):
    '''
    input point_clouds: BxNx3, np array
    return: Bx1x3
    '''
    pts_min = np.amin(point_clouds, axis=1, keepdims=True)
    pts_max = np.amax(point_clouds, axis=1, keepdims=True)
    return pts_min, pts_max

def point_bbox_center(point_clouds):
    '''
    input point_clouds: BxNx3, np array
    return: Bx1x3
    '''
    pts_min = np.amin(point_clouds, axis=1, keepdims=True)
    pts_max = np.amax(point_clouds, axis=1, keepdims=True)
    return (pts_min + pts_max) / 2.0

def point_cloud_normalized(point_clouds, tol=0.0):
    '''
    normalize the point cloud into a unit cube [-.5,.5] centered at the original
    move point cloud center to original point
    input point_clouds: BxNx3, np array
    tol: leave a margin
    '''
    pts_min, pts_max = point_bbox(point_clouds)

    bbox_size = pts_max - pts_min # B x 1 x 3
    
    scale_factor = (1.0 - tol) / np.amax(np.squeeze(bbox_size), axis=-1)
    scale_factor = np.expand_dims(scale_factor, axis=-1)
    scale_factor = np.expand_dims(scale_factor, axis=-1)

    res_pc = point_clouds - pts_min
    res_pc = res_pc * scale_factor

    cur_center = point_bbox_center(res_pc)
    delta = cur_center - [[0.0,0.0,0.0]]

    res_pc = res_pc - delta
    
    return res_pc

def remove_duplicated_points(points, tol=0.0001):
    '''
    input is a numpy array: Nx3
    '''
    fake_faces = np.array([[0,1,2]])
    mesh = pymesh.form_mesh(points, fake_faces)
    mesh, info = pymesh.remove_duplicated_vertices(mesh, tol)
    print('#Merged points: {}'.format(info["num_vertex_merged"]))
    return mesh.vertices

def add_gaussian_noise(points, noise_mu=0, noise_sigma=0.0012):
    '''
    input np.array Nx3, add gaussion distribution noise to points
    '''
    g_noise = np.random.normal(noise_mu, noise_sigma, points.shape)
    noisy_points = points + g_noise
    return noisy_points

def rotate_point_cloud(points, transformation_mat):

    new_points = np.dot(transformation_mat, points.T).T

    return new_points

def rotate_point_cloud_by_axis_angle(points, axis, angle_deg):

    angle = math.radians(angle_deg)
    rot_m = pymesh.Quaternion.fromAxisAngle(axis, angle)
    rot_m = rot_m.to_matrix()

    new_points = rotate_point_cloud(points, rot_m)

    return new_points

def sample_point_cloud(points, sample_nb):
    '''
    points: Nx3
    '''
    if points.shape[0] < sample_nb:
        replace = True
    else:
        replace = False
    choice = np.random.choice(len(points), sample_nb, replace=replace)
    return points[choice]

# ----------------------------------------
# Simple Point cloud and Volume Renderers
# ----------------------------------------

def draw_point_cloud(input_points, canvasSize=500, space=200, diameter=25,
                     xrot=0, yrot=0, zrot=0, switch_xyz=[0,1,2], normalize=True):
    """ Render point cloud to image with alpha channel.
        Input:
            points: Nx3 numpy array (+y is up direction)
        Output:
            gray image as numpy array of size canvasSizexcanvasSize
    """
    image = np.zeros((canvasSize, canvasSize))
    if input_points is None or input_points.shape[0] == 0:
        return image

    points = input_points[:, switch_xyz]
    M = euler2mat(zrot, yrot, xrot)
    points = (np.dot(M, points.transpose())).transpose()

    # Normalize the point cloud
    # We normalize scale to fit points in a unit sphere
    if normalize:
        centroid = np.mean(points, axis=0)
        points -= centroid
        furthest_distance = np.max(np.sqrt(np.sum(abs(points)**2,axis=-1)))
        points /= furthest_distance

    # Pre-compute the Gaussian disk
    radius = (diameter-1)/2.0
    disk = np.zeros((diameter, diameter))
    for i in range(diameter):
        for j in range(diameter):
            if (i - radius) * (i-radius) + (j-radius) * (j-radius) <= radius * radius:
                disk[i, j] = np.exp((-(i-radius)**2 - (j-radius)**2)/(radius**2))
    mask = np.argwhere(disk > 0)
    dx = mask[:, 0]
    dy = mask[:, 1]
    dv = disk[disk > 0]
    
    # Order points by z-buffer
    zorder = np.argsort(points[:, 2])
    points = points[zorder, :]
    points[:, 2] = (points[:, 2] - np.min(points[:, 2])) / (np.max(points[:, 2] - np.min(points[:, 2])))
    max_depth = np.max(points[:, 2])
       
    for i in range(points.shape[0]):
        j = points.shape[0] - i - 1
        x = points[j, 0]
        y = points[j, 1]
        xc = canvasSize/2 + (x*space)
        yc = canvasSize/2 + (y*space)
        xc = int(np.round(xc))
        yc = int(np.round(yc))
        
        px = dx + xc
        py = dy + yc
        
        image[px, py] = image[px, py] * 0.7 + dv * (max_depth - points[j, 2]) * 0.3
    
    image = image / np.max(image)
    return image

def point_cloud_three_views(points):
    """ input points Nx3 numpy array (+y is up direction).
        return an numpy array gray image of size 500x1500. """ 
    # +y is up direction
    # xrot is azimuth
    # yrot is in-plane
    # zrot is elevation
    img1 = draw_point_cloud(points, zrot=110/180.0*np.pi, xrot=45/180.0*np.pi, yrot=0/180.0*np.pi)
    img2 = draw_point_cloud(points, zrot=70/180.0*np.pi, xrot=135/180.0*np.pi, yrot=0/180.0*np.pi)
    img3 = draw_point_cloud(points, zrot=180.0/180.0*np.pi, xrot=90/180.0*np.pi, yrot=0/180.0*np.pi)
    image_large = np.concatenate([img1, img2, img3], 1)
    return image_large

def point_cloud_three_views_demo():
    """ Demo for draw_point_cloud function """
    from PIL import Image
    points = read_ply('../third_party/mesh_sampling/piano.ply')
    im_array = point_cloud_three_views(points)
    img = Image.fromarray(np.uint8(im_array*255.0))
    img.save('piano.jpg')

def pyplot_draw_point_cloud(points, output_filename):
    """ points is a Nx3 numpy array """
    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(points[:,0], points[:,1], points[:,2])
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_zlabel('z')
    #savefig(output_filename)

def pyplot_draw_volume(vol, output_filename):
    """ vol is of size vsize*vsize*vsize
        output an image to output_filename
    """
    points = volume_to_point_cloud(vol)
    pyplot_draw_point_cloud(points, output_filename)

if __name__=="__main__":
    import math
    point_cloud = read_ply('/workspace/pointnet2/pc2pc/run/log_ae_emd_chair_2048_test_good/pcloud/input/1.ply')
    img = draw_point_cloud(point_cloud, diameter=10, xrot=-math.pi/6.0, yrot=-math.pi/8.0, zrot=math.pi/2.0)
    from PIL import Image
    img = Image.fromarray(np.uint8(img*255))
    img.save('draw_pc.png')

