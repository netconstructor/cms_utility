<?php
/*
Plugin Name:    WP Featured Image XML-RPC Methods
Plugin URI:     http://github.com/dkukral/cms_utility/
Description:    XML Methods to get/set WP Featured Image
Version:        0.1
Author:         Don Kukral
Author URI:     http://github.com/dkukral/
*/

function check_xmlrpc($username, $password) {
    
	if ( !get_option( 'enable_xmlrpc' ) ) {
		return new IXR_Error( 405, sprintf( __( 'XML-RPC services are disabled on this blog.  An admin user can enable them at %s'),  
		    admin_url('options-writing.php') ) );
    }

	$user = wp_authenticate($username, $password);
	if (is_wp_error($user)) {
        return new IXR_Error(403, __('Bad login/pass combination.'));
	}
	
	return true;
}


add_filter('xmlrpc_methods', 'wp_featured_xmlrpc_methods');

function wp_featured_xmlrpc_methods($methods) {
    $methods['wpfeatured.getFeatured'] = 'get_featured';
    $methods['wpfeatured.getImageId'] = 'get_image_id';
    $methods['wpfeatured.setFeatured'] = 'set_featured';
    return $methods;
}

function get_featured($args) {
    global $wpdb;
    $wpdb->escape($args);
        
	$post_ID     = (int) $args[0];
	$username  = $args[1];
	$password   = $args[2];

    $error = check_xmlrpc($username, $password);
    if (is_a($error, 'IXR_Error')) { return $error; }

    if (!get_post($post_ID)) { return new IXR_Error(404, 'Post does not exist'); }

    $thumbnail_id = get_post_thumbnail_id($post_ID);
    
    return $thumbnail_id;
}

function set_featured($args) {
    global $wpdb;
    $wpdb->escape($args);
        
	$post_ID     = (int) $args[0];
	$thumb_ID    = (int) $args[1];
	$username  = $args[2];
	$password   = $args[3];

    $error = check_xmlrpc($username, $password);
    if (is_a($error, 'IXR_Error')) { return $error; }

    if (!get_post($post_ID)) { return new IXR_Error(404, 'Post does not exist'); }
    
    update_post_meta($post_ID, '_thumbnail_id', $thumb_ID);	
	
	return Array($post_ID, $thumb_ID);
}
function get_image_id($args) {
    global $wpdb;
    $wpdb->escape($args);
        
	$guid     = $args[0];
	$username  = $args[1];
	$password   = $args[2];

    $error = check_xmlrpc($username, $password);
    if (is_a($error, 'IXR_Error')) { return $error; }
	
	$query = "SELECT id FROM " . $wpdb->posts . " WHERE guid='" . $guid . "'";
	
	$image = $wpdb->get_row($query);
	
	return $image->id;
}
?>